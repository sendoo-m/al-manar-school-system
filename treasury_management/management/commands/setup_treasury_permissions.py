# treasury_management/management/commands/setup_treasury_permissions.py
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db import transaction

# استخدام get_user_model للحصول على نموذج المستخدم الصحيح
User = get_user_model()

class Command(BaseCommand):
    help = 'إعداد نظام صلاحيات الخزينة المتكامل'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='إعادة تعيين جميع المجموعات والصلاحيات',
        )
        parser.add_argument(
            '--create-demo-users',
            action='store_true',
            help='إنشاء مستخدمين تجريبيين',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 بدء إعداد نظام صلاحيات الخزينة...')
        )

        try:
            with transaction.atomic():
                if options['reset']:
                    self.reset_permissions()
                
                self.create_groups()
                self.assign_permissions()
                
                if options['create_demo_users']:
                    self.create_demo_users()
                
                self.display_summary()
                
        except Exception as e:
            raise CommandError(f'❌ خطأ في الإعداد: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS('✅ تم إعداد نظام الصلاحيات بنجاح!')
        )

    def reset_permissions(self):
        """إعادة تعيين المجموعات"""
        self.stdout.write('🔄 إعادة تعيين المجموعات...')
        
        treasury_groups = Group.objects.filter(name__startswith='treasury_')
        deleted_count = treasury_groups.count()
        treasury_groups.delete()
        
        self.stdout.write(f'🗑️ تم حذف {deleted_count} مجموعة')

    def create_groups(self):
        """إنشاء مجموعات الصلاحيات"""
        self.stdout.write('📁 إنشاء مجموعات الصلاحيات...')
        
        groups_data = [
            ('treasury_admin', 'مدير الخزينة العام', '🔴'),
            ('treasury_manager', 'مدير الخزينة', '🟠'),
            ('treasury_accountant', 'محاسب الخزينة', '🟡'),
            ('treasury_cashier', 'أمين الخزينة', '🟢'),
            ('treasury_viewer', 'مراجع الخزينة', '🔵'),
        ]
        
        for group_name, description, icon in groups_data:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'  ✅ {icon} {description} ({group_name})')
            else:
                self.stdout.write(f'  🔄 {icon} {description} (موجود)')

    def assign_permissions(self):
        """تعيين الصلاحيات للمجموعات"""
        self.stdout.write('🔐 تعيين الصلاحيات...')
        
        # الحصول على المجموعات
        groups = {
            'admin': Group.objects.get(name='treasury_admin'),
            'manager': Group.objects.get(name='treasury_manager'),
            'accountant': Group.objects.get(name='treasury_accountant'),
            'cashier': Group.objects.get(name='treasury_cashier'),
            'viewer': Group.objects.get(name='treasury_viewer'),
        }

        # محاولة الحصول على الصلاحيات
        try:
            # استيراد النماذج بشكل ديناميكي
            from treasury_management.models import Treasury, Account, Transaction
            
            # محاولة استيراد Expense إذا كان موجود
            try:
                from treasury_management.models import Expense
                models = [Treasury, Account, Transaction, Expense]
                self.stdout.write('📦 تم العثور على جميع النماذج')
            except ImportError:
                models = [Treasury, Account, Transaction]
                self.stdout.write('📦 تم العثور على النماذج الأساسية (بدون Expense)')
            
            # الحصول على أنواع المحتوى
            content_types = [ContentType.objects.get_for_model(model) for model in models]

            # صلاحيات مدير الخزينة العام (كل شيء)
            admin_perms = Permission.objects.filter(content_type__in=content_types)
            groups['admin'].permissions.set(admin_perms)
            self.stdout.write(f'  🔴 مدير عام: {admin_perms.count()} صلاحية')

            # صلاحيات مدير الخزينة
            manager_codenames = [
                'view_treasury', 'add_treasury', 'change_treasury',
                'view_account', 'add_account', 'change_account',
                'view_transaction', 'add_transaction', 'change_transaction',
            ]
            # إضافة صلاحيات Expense إذا كان متوفر
            if len(models) > 3:  # يعني Expense متوفر
                manager_codenames.extend(['view_expense', 'add_expense', 'change_expense'])
            
            manager_perms = Permission.objects.filter(
                content_type__in=content_types,
                codename__in=manager_codenames
            )
            groups['manager'].permissions.set(manager_perms)
            self.stdout.write(f'  🟠 مدير خزينة: {manager_perms.count()} صلاحية')

            # صلاحيات المحاسب
            accountant_codenames = [
                'view_treasury', 'view_account', 'add_account', 'change_account',
                'view_transaction', 'add_transaction', 'change_transaction',
            ]
            if len(models) > 3:
                accountant_codenames.extend(['view_expense', 'add_expense', 'change_expense'])
            
            accountant_perms = Permission.objects.filter(
                content_type__in=content_types,
                codename__in=accountant_codenames
            )
            groups['accountant'].permissions.set(accountant_perms)
            self.stdout.write(f'  🟡 محاسب: {accountant_perms.count()} صلاحية')

            # صلاحيات أمين الخزينة
            cashier_codenames = [
                'view_treasury', 'view_account',
                'view_transaction', 'add_transaction',
            ]
            if len(models) > 3:
                cashier_codenames.extend(['view_expense', 'add_expense'])
            
            cashier_perms = Permission.objects.filter(
                content_type__in=content_types,
                codename__in=cashier_codenames
            )
            groups['cashier'].permissions.set(cashier_perms)
            self.stdout.write(f'  🟢 أمين خزينة: {cashier_perms.count()} صلاحية')

            # صلاحيات المراجع (مشاهدة فقط)
            viewer_perms = Permission.objects.filter(
                content_type__in=content_types,
                codename__startswith='view_'
            )
            groups['viewer'].permissions.set(viewer_perms)
            self.stdout.write(f'  🔵 مراجع: {viewer_perms.count()} صلاحية')

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️ تعذر تعيين صلاحيات النماذج: {e}')
            )
            self.stdout.write('💡 سيتم إنشاء المجموعات فقط')

    def create_demo_users(self):
        """إنشاء مستخدمين تجريبيين"""
        self.stdout.write('👥 إنشاء مستخدمين تجريبيين...')
        
        demo_users = [
            ('treasury_admin_demo', 'مدير خزينة عام تجريبي', 'treasury_admin'),
            ('treasury_manager_demo', 'مدير خزينة تجريبي', 'treasury_manager'),
            ('treasury_accountant_demo', 'محاسب تجريبي', 'treasury_accountant'),
            ('treasury_cashier_demo', 'أمين خزينة تجريبي', 'treasury_cashier'),
            ('treasury_viewer_demo', 'مراجع تجريبي', 'treasury_viewer'),
        ]
        
        for username, full_name, group_name in demo_users:
            try:
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': full_name,
                        'email': f'{username}@demo.com',
                        'is_active': True,
                    }
                )
                
                if created:
                    user.set_password('demo123456')
                    user.save()
                    
                    # إضافة للمجموعة
                    group = Group.objects.get(name=group_name)
                    user.groups.add(group)
                    
                    self.stdout.write(f'  ✅ {username} - {full_name}')
                else:
                    self.stdout.write(f'  🔄 {username} موجود مسبقاً')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ خطأ في إنشاء {username}: {e}')

    def display_summary(self):
        """عرض ملخص الإعداد"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 ملخص نظام الصلاحيات'))
        self.stdout.write('='*50)
        
        groups = Group.objects.filter(name__startswith='treasury_')
        
        for group in groups:
            users_count = group.user_set.count()
            permissions_count = group.permissions.count()
            
            icon = {
                'treasury_admin': '🔴',
                'treasury_manager': '🟠', 
                'treasury_accountant': '🟡',
                'treasury_cashier': '🟢',
                'treasury_viewer': '🔵',
            }.get(group.name, '⚪')
            
            self.stdout.write(
                f'{icon} {group.name}: {users_count} مستخدمين، {permissions_count} صلاحية'
            )
        
        self.stdout.write('\n💡 لإضافة مستخدم لمجموعة في Django Admin:')
        self.stdout.write('   الذهاب لـ Users -> اختيار المستخدم -> Groups -> إضافة المجموعة')
        
        self.stdout.write('\n🔑 كلمات المرور للمستخدمين التجريبيين: demo123456')
