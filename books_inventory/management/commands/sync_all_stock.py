from django.core.management.base import BaseCommand
from books_inventory.models import Book

class Command(BaseCommand):
    help = 'تحديث مخزون جميع الكتب من إيصالات الاستلام'

    def handle(self, *args, **options):
        books = Book.objects.all()
        updated_count = 0
        
        for book in books:
            old_stock = book.total_stock
            book.sync_stock_from_receipts()
            if book.total_stock != old_stock:
                updated_count += 1
                self.stdout.write(
                    f'تم تحديث {book.title}: {old_stock} -> {book.total_stock}'
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'تم تحديث {updated_count} كتاب من أصل {books.count()}')
        )
