from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from certificates.models import Student, CertificateRequest, GeneratedCertificate

class Command(BaseCommand):
    help = 'Clears all student data and non-staff users for a fresh start.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Starting cleanup process...'))

        # 1. Requests aur Certificates Delete karein
        # (GeneratedCertificate apne aap delete ho jayega kyunki wo Request se juda hai CASCADE ke through)
        req_count = CertificateRequest.objects.count()
        CertificateRequest.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {req_count} Certificate Requests (and associated Certificates).'))

        # 2. Students Delete karein
        # (Ab student delete ho sakte hain kyunki requests hat gayi hain)
        std_count = Student.objects.count()
        Student.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {std_count} Student records from Database.'))

        # 3. Users Delete karein (Sirf Students wale)
        # Hum check karenge ki wo Staff ya Superuser NA ho.
        users_to_delete = User.objects.filter(is_staff=False, is_superuser=False)
        user_count = users_to_delete.count()
        users_to_delete.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {user_count} User accounts (Students).'))

        self.stdout.write(self.style.SUCCESS('------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS('COMPLETE: Database is now clean for fresh import.'))
        self.stdout.write(self.style.SUCCESS('Admin and Staff accounts are SAFE.'))