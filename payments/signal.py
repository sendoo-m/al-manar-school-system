# في payments/models.py - إضافة signal
from django.db.models.signals import post_save
from django.dispatch import receiver
from treasury_management.models import Transaction, StudentPaymentTransaction

@receiver(post_save, sender=StudentPayment)
def create_treasury_transaction(sender, instance, created, **kwargs):
    """إنشاء عملية مالية عند تسجيل دفعة طالب"""
    if created and instance.is_confirmed:
        from treasury_management.models import Treasury, Account
        
        # الحصول على الخزنة الرئيسية
        main_treasury = Treasury.objects.filter(is_active=True).first()
        # حساب إيرادات الطلاب
        students_revenue_account = Account.objects.get(code='4001')  # مثال
        
        if main_treasury and students_revenue_account:
            transaction = Transaction.objects.create(
                treasury=main_treasury,
                account=students_revenue_account,
                transaction_type='INCOME',
                amount=instance.paid_amount,
                description=f'دفعة من الطالب: {instance.student.name} - {instance.fee_type.name}',
                payment_method='CASH',
                related_model='StudentPayment',
                related_id=instance.id,
                created_by=instance.created_by,
                academic_year=instance.academic_year,
                is_approved=True  # اعتماد فوري للمدفوعات
            )
            
            # ربط الدفعة بالعملية
            StudentPaymentTransaction.objects.create(
                student_payment=instance,
                transaction=transaction
            )
            
            # تحديث الأرصدة
            transaction.update_balances()
