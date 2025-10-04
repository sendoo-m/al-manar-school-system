from django.core.management.base import BaseCommand
from books_inventory.models import Notebook
from students.models import GradeLevel
from decimal import Decimal

class Command(BaseCommand):
    help = 'إنشاء جميع أنواع الكراسات المدرسية بناءً على النظام الفعلي'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📓 بدء إنشاء أنواع الكراسات...'))
        
        # التحقق من الحقول المتاحة في نموذج Notebook
        notebook_fields = [f.name for f in Notebook._meta.get_fields()]
        self.stdout.write(f'🔍 الحقول المتاحة في Notebook: {notebook_fields}')
        
        # أنواع الكراسات بناءً على النظام الفعلي
        notebook_types = [
            # كراسات اللغة العربية - مسطر
            {
                'name': 'لغة عربية - مسطر - 40 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 40
            },
            {
                'name': 'لغة عربية - مسطر - 80 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 80
            },
            
            # كراسات اللغة الإنجليزية - مسطر
            {
                'name': 'لغة إنجليزية - مسطر - 40 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 40
            },
            {
                'name': 'لغة إنجليزية - مسطر - 80 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 80
            },
            
            # كراسات الرياضيات - مربعات
            {
                'name': 'رياضيات - مربعات - 40 ورقة',
                'notebook_type': 'GRAPH',
                'pages_count': 40
            },
            
            # كراسات العلوم - وجه وجه
            {
                'name': 'علوم - وجه وجه - 40 ورقة',
                'notebook_type': 'MIXED',
                'pages_count': 40
            },
            
            # كراسات الرسم - 20 ورقة
            {
                'name': 'رسم - أبيض - 20 ورقة - حجم كبير',
                'notebook_type': 'BLANK',
                'pages_count': 20
            },
            
            {
                'name': 'رسم - أبيض - 20 ورقة - حجم متوسط',
                'notebook_type': 'BLANK',
                'pages_count': 20
            },
            
            # كراسات الدراسات الاجتماعية
            {
                'name': 'دراسات اجتماعية - مسطر - 40 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 40
            },
            
            # كراسات التربية الدينية
            {
                'name': 'تربية دينية - مسطر - 40 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 40
            },
            
            # كراسات التربية الفنية
            {
                'name': 'تربية فنية - رسم - 20 ورقة',
                'notebook_type': 'DRAWING',
                'pages_count': 20
            },
            
            # كراسات الحاسوب
            {
                'name': 'حاسوب - مسطر - 40 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 40
            },
            
            # كراسات التسميع والاختبارات
            {
                'name': 'تسميع - مسطر - 20 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 20
            },
            
            # كراسات الواجبات
            {
                'name': 'واجبات - مسطر - 40 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 40
            },
            
            # كراسات المراجعة
            {
                'name': 'مراجعة - مسطر - 80 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 80
            },
            
            # كراسات للمناهج الأجنبية
            {
                'name': 'منهج أمريكي - مسطر - 40 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 40
            },
            
            {
                'name': 'منهج بريطاني - مسطر - 40 ورقة',
                'notebook_type': 'LINED',
                'pages_count': 40
            },
            
            # كراسات المواد المتقدمة
            {
                'name': 'فيزياء - مربعات - 40 ورقة',
                'notebook_type': 'GRAPH',
                'pages_count': 40
            },
            
            {
                'name': 'كيمياء - مربعات - 40 ورقة',
                'notebook_type': 'GRAPH',
                'pages_count': 40
            },
            
            {
                'name': 'أحياء - وجه وجه - 40 ورقة',
                'notebook_type': 'MIXED',
                'pages_count': 40
            },
            
            # كراسات التربية الموسيقية
            {
                'name': 'تربية موسيقية - مخطط موسيقى - 40 ورقة',
                'notebook_type': 'MUSICAL',
                'pages_count': 40
            },
            
            # كراسات الجغرافيا
            {
                'name': 'جغرافيا - خرائط - 40 ورقة',
                'notebook_type': 'MAP',
                'pages_count': 40
            }
        ]

        created_count = 0
        
        try:
            # الحصول على جميع الصفوف الدراسية لربطها بالكراسات
            all_grades = list(GradeLevel.objects.all())
            
            for notebook_data in notebook_types:
                # تحضير البيانات الأساسية
                defaults = {
                    'notebook_type': notebook_data['notebook_type'],
                    'pages_count': notebook_data['pages_count'],
                    'minimum_stock_level': 100,  # حد أدنى 100 كراسة
                    'is_active': True,
                    'total_stock': 0,
                    'available_stock': 0,
                    'distributed_count': 0,
                    'damaged_count': 0
                }
                
                # إضافة الحقول الإضافية إذا كانت موجودة
                if 'cost_price' in notebook_fields:
                    defaults['cost_price'] = Decimal('0.00')
                
                notebook, created = Notebook.objects.get_or_create(
                    name=notebook_data['name'],
                    defaults=defaults
                )
                
                if created:
                    # ربط الكراسة بجميع الصفوف الدراسية إذا كان الحقل موجود
                    if hasattr(notebook, 'grade_levels') and all_grades:
                        notebook.grade_levels.set(all_grades)
                    
                    created_count += 1
                    type_emoji = self._get_type_emoji(notebook_data['notebook_type'])
                    
                    self.stdout.write(
                        f'{type_emoji} تم إنشاء: {notebook_data["name"]}'
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'🎉 تم إنشاء {created_count} نوع كراسة بنجاح!')
            )
            
            # إحصائيات سريعة
            total_notebooks = Notebook.objects.count()
            
            self.stdout.write(
                self.style.SUCCESS(f'''
📊 إحصائيات الكراسات:
   📓 إجمالي أنواع الكراسات: {total_notebooks}
   ✨ الكراسات الجديدة: {created_count}
                ''')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ خطأ في إنشاء الكراسات: {e}')
            )
            import traceback
            self.stdout.write(self.style.ERROR(f'تفاصيل الخطأ: {traceback.format_exc()}'))

    def _get_type_emoji(self, notebook_type):
        """الحصول على emoji حسب النوع"""
        type_map = {
            'LINED': '📝',
            'GRAPH': '📊',
            'BLANK': '🎨',
            'MIXED': '📋',
            'DRAWING': '🖼️',
            'MUSICAL': '🎵',
            'MAP': '🗺️',
            'CHART': '📈'
        }
        return type_map.get(notebook_type, '📓')
