# fix_duplicate_treasury_account_links.py
"""
تصحيح ربط حسابات الخزائن المكررة.

المشكلة التي يعالجها:
- صفحة الخزائن تعرض الخزنة الرئيسية برصيد صحيح، مثل 16600.
- صفحة الحسابات تعرض حسابًا آخر باسم قريب، مثل "حساب الخزنة الرئيسية" بكود 10001 ورصيد مختلف.
- السبب أن الخزنة مرتبطة فعليًا بحساب آخر، مثل CASH-MAIN، بينما الحساب 10001 حساب قديم أو مكرر وغير مربوط بالخزنة.

ما يفعله السكربت:
1) يبحث لكل خزنة عن حساب أصل/خزنة مناسب بالاسم.
2) إذا وجد حسابًا قديمًا مناسبًا غير مربوط بأي خزنة، يربط الخزنة به.
3) ينقل الرصيد الصحيح الحالي من الحساب المرتبط القديم إلى الحساب الجديد.
4) يعطل الحساب القديم إذا لم يكن عليه عمليات مباشرة.
5) يطبع تقريرًا واضحًا بما حدث.

طريقة التشغيل من PowerShell داخل مجلد المشروع بجانب manage.py:

python manage.py shell -c "exec(open('fix_duplicate_treasury_account_links.py', encoding='utf-8').read())"
"""

from decimal import Decimal
import re

from django.db import transaction as db_transaction
from django.db.models import Q

from treasury_management.models import Account, Treasury, Transaction


def normalize_ar(text):
    text = (text or '').strip()
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
    text = text.replace('ة', 'ه')
    text = re.sub(r'\s+', ' ', text)
    return text


def score_candidate(treasury, account):
    """
    إعطاء درجة للحساب المرشح حتى نختار الأقرب للخزنة.
    """
    t_name = normalize_ar(treasury.name)
    a_name = normalize_ar(account.name)
    a_code = normalize_ar(account.code)

    score = 0

    # تطابق الاسم الكامل
    if t_name and t_name in a_name:
        score += 100

    # وجود كلمة خزنة/الخزنة
    if 'خزنه' in a_name or 'الخزنه' in a_name:
        score += 30

    # خزنة رئيسية
    if ('رئيسيه' in t_name or treasury.code.upper() in ['MAIN', 'MAIN-TREASURY']) and ('رئيسيه' in a_name or a_code in ['10001', '1001']):
        score += 80

    # خزنة فرعية
    if ('فرعيه' in t_name or treasury.code.upper() in ['SECONDARY', 'SEC']) and ('فرعيه' in a_name or a_code in ['10002', '1002']):
        score += 80

    # يفضّل الحسابات ذات الأكواد الرقمية القديمة إذا كانت ظاهرة في الشاشة
    if a_code.isdigit():
        score += 10

    # لا نختار حساب عليه خزنة أخرى
    if hasattr(account, 'treasury'):
        score -= 1000

    # لا نختار حساب إيراد/مصروف
    if account.category.category_type != 'ASSET':
        score -= 1000

    return score


def choose_best_account_for_treasury(treasury, all_asset_accounts):
    current_account = treasury.account
    candidates = []

    for account in all_asset_accounts:
        if account.id == current_account.id:
            continue

        # تجاهل أي حساب مربوط بخزنة أخرى
        if Treasury.objects.filter(account=account).exclude(id=treasury.id).exists():
            continue

        s = score_candidate(treasury, account)
        if s > 0:
            candidates.append((s, account))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


@db_transaction.atomic
def run():
    print("=" * 90)
    print("تصحيح ربط حسابات الخزائن المكررة")
    print("=" * 90)

    asset_accounts = list(
        Account.objects.select_related('category').filter(category__category_type='ASSET')
    )

    changed_count = 0

    for treasury in Treasury.objects.select_related('account', 'account__category').all().order_by('code'):
        old_account = treasury.account
        real_balance = old_account.current_balance or Decimal('0.00')

        print()
        print(f"الخزنة: {treasury.code} - {treasury.name}")
        print(f"الحساب الحالي المرتبط: {old_account.code} - {old_account.name}")
        print(f"الرصيد الصحيح الحالي: {real_balance}")

        new_account = choose_best_account_for_treasury(treasury, asset_accounts)

        if not new_account:
            print("✅ لا يوجد حساب مكرر مناسب. سيتم الإبقاء على الربط الحالي.")
            continue

        print(f"الحساب المرشح للربط: {new_account.code} - {new_account.name}")
        print(f"رصيده قبل التصحيح: {new_account.current_balance}")

        # انقل الرصيد الصحيح للحساب الجديد
        new_account.current_balance = real_balance
        new_account.is_active = True
        if not new_account.description:
            new_account.description = f"الحساب المالي المرتبط بالخزنة: {treasury.name}"
        new_account.save(update_fields=['current_balance', 'is_active', 'description', 'updated_at'])

        # اربط الخزنة بالحساب الجديد
        treasury.account = new_account
        treasury.save(update_fields=['account'])

        changed_count += 1

        # عطّل الحساب القديم فقط إذا لم يكن عليه عمليات مباشرة
        old_account_transactions = Transaction.objects.filter(account=old_account).count()

        if old_account_transactions == 0:
            old_account.current_balance = Decimal('0.00')
            old_account.is_active = False
            old_account.description = (
                (old_account.description or '') +
                f"\n[تم تعطيله تلقائيًا لأنه كان حساب خزنة مكررًا، وتم نقل الربط إلى {new_account.code}]"
            ).strip()
            old_account.save(update_fields=['current_balance', 'is_active', 'description', 'updated_at'])
            print(f"⚠️ تم تعطيل الحساب القديم: {old_account.code} لأنه لا يحتوي على عمليات مباشرة.")
        else:
            print(
                f"⚠️ لم يتم تعطيل الحساب القديم {old_account.code} لأنه يحتوي على "
                f"{old_account_transactions} عملية مباشرة. راجعه يدويًا."
            )

        print(f"✅ تم ربط {treasury.name} بالحساب {new_account.code} وتحديث رصيده إلى {real_balance}")

    print()
    print("=" * 90)
    print(f"تم تصحيح {changed_count} خزنة.")
    print("=" * 90)

    print()
    print("النتيجة الحالية:")
    for treasury in Treasury.objects.select_related('account').all().order_by('code'):
        print(
            f"- {treasury.code} - {treasury.name}: "
            f"الحساب {treasury.account.code} - {treasury.account.name} | "
            f"الرصيد {treasury.current_balance}"
        )


run()
