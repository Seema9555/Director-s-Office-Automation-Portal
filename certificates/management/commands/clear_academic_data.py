from django.core.management.base import BaseCommand
from certificates.models import Teacher, Subject, CourseAllocation

class Command(BaseCommand):
    help = 'Deletes all academic data (Teachers, Subjects, Allocations) to reset the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("⚠️  Starting Data Cleanup..."))

        # 1. Delete Allocations first (Child table)
        count_alloc, _ = CourseAllocation.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"   🗑️  Deleted {count_alloc} Course Allocations."))

        # 2. Delete Teachers
        count_teach, _ = Teacher.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"   🗑️  Deleted {count_teach} Teachers."))

        # 3. Delete Subjects
        count_subj, _ = Subject.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"   🗑️  Deleted {count_subj} Subjects."))

        self.stdout.write(self.style.SUCCESS("\n✅ Database is now clean! You can re-import correctly."))