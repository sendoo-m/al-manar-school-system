from decimal import Decimal

from django.db.models import Sum

from school_settings.models import SchoolFeesSettings


class StudentFinancialService:
    """
    خدمة موحدة لحساب الحالة المالية للطالب
    حسب الصف الدراسي والعام الدراسي.
    """

    @staticmethod
    def get_student_required_fees(student, academic_year=None):
        """
        إجمالي المصروفات المطلوبة للطالب حسب صفه والعام الدراسي.
        """
        if not student or not student.grade_level:
            return Decimal('0.00')

        year = academic_year or student.academic_year

        if not year:
            return Decimal('0.00')

        total = SchoolFeesSettings.objects.filter(
            academic_year=year,
            grade_level=student.grade_level,
            is_active=True
        ).aggregate(
            total=Sum('total_amount')
        )['total']

        return total or Decimal('0.00')

    @staticmethod
    def get_student_payments(student):
        """
        إجمالي المدفوعات المسجلة على الطالب.
        حالياً يعتمد على student.total_payments.
        لاحقاً يمكن ربطه بجدول مدفوعات مستقل.
        """
        if not student:
            return Decimal('0.00')

        return student.total_payments or Decimal('0.00')

    @classmethod
    def get_student_balance(cls, student, academic_year=None):
        """
        حساب ملخص الطالب المالي.
        """
        required_fees = cls.get_student_required_fees(student, academic_year)
        paid_amount = cls.get_student_payments(student)
        owed_amount = required_fees - paid_amount

        if owed_amount < 0:
            owed_amount = Decimal('0.00')

        return {
            'required_fees': required_fees,
            'paid_amount': paid_amount,
            'owed_amount': owed_amount,
            'is_paid': owed_amount <= 0,
            'collection_percentage': (
                paid_amount / required_fees * 100
            ) if required_fees > 0 else 0,
        }

    @classmethod
    def sync_student_financial_fields(cls, student, academic_year=None, save=True):
        """
        تحديث الحقول المالية المخزنة داخل Student
        بناءً على إعدادات المصروفات الحالية.
        """
        balance = cls.get_student_balance(student, academic_year)

        student.total_fees = balance['required_fees']
        student.total_owed = balance['owed_amount']

        if save:
            student.save(update_fields=['total_fees', 'total_owed', 'updated_at'])

        return student