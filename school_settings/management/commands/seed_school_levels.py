from django.core.management.base import BaseCommand
from school_settings.models import EducationLevel, GradeLevel


class Command(BaseCommand):
    help = "إضافة المراحل التعليمية والصفوف الدراسية الافتراضية"

    def handle(self, *args, **options):
        data = [
            {
                "name": "رياض الأطفال منار1",
                "name_en": "KG Manar 1",
                "min_age": 4,
                "max_age": 5,
                "order": 1,
                "grades": [
                    {"name": "KG1", "name_en": "KG1", "grade_number": 1, "typical_age": 4, "order": 1},
                    {"name": "KG2", "name_en": "KG2", "grade_number": 2, "typical_age": 5, "order": 2},
                ],
            },
            {
                "name": "رياض الأطفال منار2",
                "name_en": "KG Manar 2",
                "min_age": 4,
                "max_age": 5,
                "order": 2,
                "grades": [
                    {"name": "KG1", "name_en": "KG1", "grade_number": 1, "typical_age": 4, "order": 1},
                    {"name": "KG2", "name_en": "KG2", "grade_number": 2, "typical_age": 5, "order": 2},
                ],
            },
            {
                "name": "المرحلة الابتدائية منار1",
                "name_en": "Primary Manar 1",
                "min_age": 6,
                "max_age": 11,
                "order": 3,
                "grades": [
                    {"name": "الصف الأول", "name_en": "Grade 1", "grade_number": 1, "typical_age": 6, "order": 1},
                    {"name": "الصف الثاني", "name_en": "Grade 2", "grade_number": 2, "typical_age": 7, "order": 2},
                    {"name": "الصف الثالث", "name_en": "Grade 3", "grade_number": 3, "typical_age": 8, "order": 3},
                    {"name": "الصف الرابع", "name_en": "Grade 4", "grade_number": 4, "typical_age": 9, "order": 4},
                    {"name": "الصف الخامس", "name_en": "Grade 5", "grade_number": 5, "typical_age": 10, "order": 5},
                    {"name": "الصف السادس", "name_en": "Grade 6", "grade_number": 6, "typical_age": 11, "order": 6},
                ],
            },
            {
                "name": "المرحلة الابتدائية منار2",
                "name_en": "Primary Manar 2",
                "min_age": 6,
                "max_age": 11,
                "order": 4,
                "grades": [
                    {"name": "الصف الأول", "name_en": "Grade 1", "grade_number": 1, "typical_age": 6, "order": 1},
                    {"name": "الصف الثاني", "name_en": "Grade 2", "grade_number": 2, "typical_age": 7, "order": 2},
                    {"name": "الصف الثالث", "name_en": "Grade 3", "grade_number": 3, "typical_age": 8, "order": 3},
                    {"name": "الصف الرابع", "name_en": "Grade 4", "grade_number": 4, "typical_age": 9, "order": 4},
                    {"name": "الصف الخامس", "name_en": "Grade 5", "grade_number": 5, "typical_age": 10, "order": 5},
                    {"name": "الصف السادس", "name_en": "Grade 6", "grade_number": 6, "typical_age": 11, "order": 6},
                ],
            },
            {
                "name": "المرحلة الإعدادية منار1",
                "name_en": "Preparatory Manar 1",
                "min_age": 12,
                "max_age": 14,
                "order": 5,
                "grades": [
                    {"name": "الصف الأول الإعدادي", "name_en": "Prep 1", "grade_number": 1, "typical_age": 12, "order": 1},
                    {"name": "الصف الثاني الإعدادي", "name_en": "Prep 2", "grade_number": 2, "typical_age": 13, "order": 2},
                    {"name": "الصف الثالث الإعدادي", "name_en": "Prep 3", "grade_number": 3, "typical_age": 14, "order": 3},
                ],
            },
            {
                "name": "المرحلة الإعدادية منار2",
                "name_en": "Preparatory Manar 2",
                "min_age": 12,
                "max_age": 14,
                "order": 6,
                "grades": [
                    {"name": "الصف الأول الإعدادي", "name_en": "Prep 1", "grade_number": 1, "typical_age": 12, "order": 1},
                    {"name": "الصف الثاني الإعدادي", "name_en": "Prep 2", "grade_number": 2, "typical_age": 13, "order": 2},
                    {"name": "الصف الثالث الإعدادي", "name_en": "Prep 3", "grade_number": 3, "typical_age": 14, "order": 3},
                ],
            },
            {
                "name": "المرحلة الثانوية منار1",
                "name_en": "Secondary Manar 1",
                "min_age": 15,
                "max_age": 17,
                "order": 7,
                "grades": [
                    {"name": "الصف الأول الثانوي", "name_en": "Secondary 1", "grade_number": 1, "typical_age": 15, "order": 1},
                    {"name": "الصف الثاني الثانوي", "name_en": "Secondary 2", "grade_number": 2, "typical_age": 16, "order": 2},
                    {"name": "الصف الثالث الثانوي", "name_en": "Secondary 3", "grade_number": 3, "typical_age": 17, "order": 3},
                ],
            },
            {
                "name": "المرحلة الثانوية منار2",
                "name_en": "Secondary Manar 2",
                "min_age": 15,
                "max_age": 17,
                "order": 8,
                "grades": [
                    {"name": "الصف الأول الثانوي", "name_en": "Secondary 1", "grade_number": 1, "typical_age": 15, "order": 1},
                    {"name": "الصف الثاني الثانوي", "name_en": "Secondary 2", "grade_number": 2, "typical_age": 16, "order": 2},
                    {"name": "الصف الثالث الثانوي", "name_en": "Secondary 3", "grade_number": 3, "typical_age": 17, "order": 3},
                ],
            },
            {
                "name": "المدرسة الأمريكية رياض الأطفال منار1",
                "name_en": "American School KG Manar 1",
                "min_age": 4,
                "max_age": 5,
                "order": 9,
                "grades": [
                    {"name": "KG1", "name_en": "KG1", "grade_number": 1, "typical_age": 4, "order": 1},
                    {"name": "KG2", "name_en": "KG2", "grade_number": 2, "typical_age": 5, "order": 2},
                ],
            },
            {
                "name": "المدرسة الأمريكية رياض الأطفال منار2",
                "name_en": "American School KG Manar 2",
                "min_age": 4,
                "max_age": 5,
                "order": 10,
                "grades": [
                    {"name": "KG1", "name_en": "KG1", "grade_number": 1, "typical_age": 4, "order": 1},
                    {"name": "KG2", "name_en": "KG2", "grade_number": 2, "typical_age": 5, "order": 2},
                ],
            },
            {
                "name": "المدرسة الأمريكية ابتدائي منار1",
                "name_en": "American School Primary Manar 1",
                "min_age": 6,
                "max_age": 11,
                "order": 11,
                "grades": [
                    {"name": "الصف الأول", "name_en": "Grade 1", "grade_number": 1, "typical_age": 6, "order": 1},
                    {"name": "الصف الثاني", "name_en": "Grade 2", "grade_number": 2, "typical_age": 7, "order": 2},
                    {"name": "الصف الثالث", "name_en": "Grade 3", "grade_number": 3, "typical_age": 8, "order": 3},
                    {"name": "الصف الرابع", "name_en": "Grade 4", "grade_number": 4, "typical_age": 9, "order": 4},
                    {"name": "الصف الخامس", "name_en": "Grade 5", "grade_number": 5, "typical_age": 10, "order": 5},
                    {"name": "الصف السادس", "name_en": "Grade 6", "grade_number": 6, "typical_age": 11, "order": 6},
                ],
            },
            {
                "name": "المدرسة الأمريكية ابتدائي منار2",
                "name_en": "American School Primary Manar 2",
                "min_age": 6,
                "max_age": 11,
                "order": 12,
                "grades": [
                    {"name": "الصف الأول", "name_en": "Grade 1", "grade_number": 1, "typical_age": 6, "order": 1},
                    {"name": "الصف الثاني", "name_en": "Grade 2", "grade_number": 2, "typical_age": 7, "order": 2},
                    {"name": "الصف الثالث", "name_en": "Grade 3", "grade_number": 3, "typical_age": 8, "order": 3},
                    {"name": "الصف الرابع", "name_en": "Grade 4", "grade_number": 4, "typical_age": 9, "order": 4},
                    {"name": "الصف الخامس", "name_en": "Grade 5", "grade_number": 5, "typical_age": 10, "order": 5},
                    {"name": "الصف السادس", "name_en": "Grade 6", "grade_number": 6, "typical_age": 11, "order": 6},
                ],
            },
            {
                "name": "المدرسة الأمريكية إعدادي منار1",
                "name_en": "American School Preparatory Manar 1",
                "min_age": 12,
                "max_age": 14,
                "order": 13,
                "grades": [
                    {"name": "الصف الأول الإعدادي", "name_en": "Prep 1", "grade_number": 1, "typical_age": 12, "order": 1},
                    {"name": "الصف الثاني الإعدادي", "name_en": "Prep 2", "grade_number": 2, "typical_age": 13, "order": 2},
                    {"name": "الصف الثالث الإعدادي", "name_en": "Prep 3", "grade_number": 3, "typical_age": 14, "order": 3},
                ],
            },
            {
                "name": "المدرسة الأمريكية إعدادي منار2",
                "name_en": "American School Preparatory Manar 2",
                "min_age": 12,
                "max_age": 14,
                "order": 14,
                "grades": [
                    {"name": "الصف الأول الإعدادي", "name_en": "Prep 1", "grade_number": 1, "typical_age": 12, "order": 1},
                    {"name": "الصف الثاني الإعدادي", "name_en": "Prep 2", "grade_number": 2, "typical_age": 13, "order": 2},
                    {"name": "الصف الثالث الإعدادي", "name_en": "Prep 3", "grade_number": 3, "typical_age": 14, "order": 3},
                ],
            },
            {
                "name": "المدرسة الأمريكية ثانوي منار1",
                "name_en": "American School Secondary Manar 1",
                "min_age": 15,
                "max_age": 17,
                "order": 15,
                "grades": [
                    {"name": "الصف الأول الثانوي", "name_en": "Secondary 1", "grade_number": 1, "typical_age": 15, "order": 1},
                    {"name": "الصف الثاني الثانوي", "name_en": "Secondary 2", "grade_number": 2, "typical_age": 16, "order": 2},
                    {"name": "الصف الثالث الثانوي", "name_en": "Secondary 3", "grade_number": 3, "typical_age": 17, "order": 3},
                ],
            },
            {
                "name": "المدرسة الأمريكية ثانوي منار2",
                "name_en": "American School Secondary Manar 2",
                "min_age": 15,
                "max_age": 17,
                "order": 16,
                "grades": [
                    {"name": "الصف الأول الثانوي", "name_en": "Secondary 1", "grade_number": 1, "typical_age": 15, "order": 1},
                    {"name": "الصف الثاني الثانوي", "name_en": "Secondary 2", "grade_number": 2, "typical_age": 16, "order": 2},
                    {"name": "الصف الثالث الثانوي", "name_en": "Secondary 3", "grade_number": 3, "typical_age": 17, "order": 3},
                ],
            },
        ]

        created_levels = 0
        created_grades = 0

        for level_data in data:
            grades = level_data.pop("grades")

            education_level, level_created = EducationLevel.objects.get_or_create(
                name=level_data["name"],
                defaults=level_data
            )

            if not level_created:
                for field, value in level_data.items():
                    setattr(education_level, field, value)
                education_level.is_active = True
                education_level.save()

            if level_created:
                created_levels += 1
                self.stdout.write(self.style.SUCCESS(f"تم إنشاء المرحلة: {education_level.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"المرحلة موجودة مسبقًا: {education_level.name}"))

            for grade_data in grades:
                grade_level, grade_created = GradeLevel.objects.get_or_create(
                    education_level=education_level,
                    grade_number=grade_data["grade_number"],
                    defaults={
                        "name": grade_data["name"],
                        "name_en": grade_data["name_en"],
                        "typical_age": grade_data["typical_age"],
                        "order": grade_data["order"],
                        "is_active": True,
                    }
                )

                if not grade_created:
                    grade_level.name = grade_data["name"]
                    grade_level.name_en = grade_data["name_en"]
                    grade_level.typical_age = grade_data["typical_age"]
                    grade_level.order = grade_data["order"]
                    grade_level.is_active = True
                    grade_level.save()

                if grade_created:
                    created_grades += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  └─ تم إنشاء الصف: {grade_level.name} - {education_level.name}"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"  └─ الصف موجود مسبقًا: {grade_level.name} - {education_level.name}"
                    ))

        self.stdout.write(self.style.SUCCESS(
            f"\nتم الانتهاء بنجاح: {created_levels} مرحلة جديدة، {created_grades} صف جديد."
        ))