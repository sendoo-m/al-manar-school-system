# payments/management/commands/fix_discount_data.py

from django.core.management.base import BaseCommand
from payments.models import Discount

class Command(BaseCommand):
    help = 'إصلاح بيانات الخصومات'

    def handle(self, *args, **options):
        try:
            # تحديث البيانات الفارغة
            discounts_updated = Discount.objects.filter(
                discount_amount__isnull=True
            ).update(discount_amount=0)
            
            discounts_reason_updated = Discount.objects.filter(
                reason__isnull=True
            ).update(reason='خصم عام')
            
            self.stdout.write(
                self.style.SUCCESS(f'تم تحديث {discounts_updated} خصم')
            )
            
            # عرض إحصائيات
            total_discounts = Discount.objects.count()
            active_discounts = Discount.objects.filter(is_active=True).count()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'إجمالي الخصومات: {total_discounts}\n'
                    f'الخصومات النشطة: {active_discounts}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في إصلاح البيانات: {e}')
            )
