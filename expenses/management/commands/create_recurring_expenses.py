from calendar import monthrange
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from expenses.models import Expense, RecurringExpense
def add_one_month(value):
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)
class Command(BaseCommand):
    help = "Create expenses for recurring rules that are due."
    def handle(self, *args, **options):
        today = timezone.localdate()
        created_count = 0
        due_rules = RecurringExpense.objects.filter(
            is_active=True, next_run_date__lte=today
        ).select_related("user", "category")
        for rule in due_rules:
            with transaction.atomic():
                # Lock this rule to reduce duplicate processing if two
                # command processes run at the same time.
                locked = RecurringExpense.objects.select_for_update().get(
                    pk=rule.pk
                )
                while locked.is_active and locked.next_run_date <= today:
                    Expense.objects.create(
                        user=locked.user,
                        category=locked.category,
                        title=locked.title,
                        amount=locked.amount,
                        expense_date=locked.next_run_date,
                        notes="Created automatically from recurring expense.",
                    )
                    created_count += 1
                    if locked.frequency == RecurringExpense.WEEKLY:
                        locked.next_run_date += timedelta(days=7)
                    else:
                        locked.next_run_date = add_one_month(
                            locked.next_run_date
                        )
                locked.save(update_fields=["next_run_date"])
        self.stdout.write(self.style.SUCCESS(
            f"Created {created_count} recurring expense(s)."
        ))