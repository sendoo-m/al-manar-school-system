from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum

from students.models import Student
from payments.models import Tuition


class Command(BaseCommand):
    help = 'Recalculate total_fees, total_payments, and total_owed for all active students.'

    def handle(self, *args, **options):
        students = Student.objects.filter(is_active=True)
        total_students = students.count()
        updated_count = 0

        self.stdout.write(self.style.WARNING(f'بدء تحديث إجماليات {total_students} طالب...'))

        for student in students:
            installments = Tuition.objects.filter(
                student=student
            ).exclude(
                payment_status='CANCELLED'
            )

            totals = installments.aggregate(
                total_fees=Sum('amount_tuition'),
                total_payments=Sum('amount_paid'),
            )

            total_fees = totals['total_fees'] or Decimal('0.00')
            total_payments = totals['total_payments'] or Decimal('0.00')
            total_owed = max(Decimal('0.00'), total_fees - total_payments)

            student.total_fees = total_fees
            student.total_payments = total_payments
            student.total_owed = total_owed
            student.save(update_fields=['total_fees', 'total_payments', 'total_owed'])

            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'تم تحديث إجماليات {updated_count} طالب بنجاح.'))