from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expense_categories",
    )
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_category_name_per_user",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "name"], name="cat_user_name_idx"),
        ]
    def __str__(self):
        return self.name

class Expense(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    title = models.CharField(max_length=150)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    expense_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-expense_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="expense_amount_gt_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "expense_date"],
                         name="exp_user_date_idx"),
            models.Index(fields=["user", "category", "expense_date"],
                         name="exp_user_cat_date_idx"),
        ]
    def __str__(self):
        return f"{self.title} - {self.amount}"
class Budget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    month = models.DateField(help_text="Use the first day of the month.")
    limit_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    class Meta:
        ordering = ["-month", "category__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "month"],
                name="unique_budget_user_category_month",
            ),
            models.CheckConstraint(
                condition=Q(limit_amount__gt=0),
                name="budget_limit_gt_zero",
            ),
            models.CheckConstraint(
                condition=Q(month__day=1),
                name="budget_month_first_day",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "month"], name="bud_user_month_idx"),
        ]
    def __str__(self):
        return f"{self.category} - {self.month:%Y-%m}"
class RecurringExpense(models.Model):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    FREQUENCY_CHOICES = [
        (WEEKLY, "Weekly"),
        (MONTHLY, "Monthly"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_expenses",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="recurring_expenses",
    )
    title = models.CharField(max_length=150)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    next_run_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["next_run_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="recurring_amount_gt_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active", "next_run_date"],
                         name="rec_active_next_idx"),
            models.Index(fields=["user", "is_active"],
                         name="rec_user_active_idx"),
        ]
    def __str__(self):
        return f"{self.title} ({self.frequency})"		