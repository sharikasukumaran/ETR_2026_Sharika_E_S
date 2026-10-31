from rest_framework import serializers
from .models import Category, Expense, Budget, RecurringExpense
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]
    def validate_name(self, value):
        user = self.context["request"].user
        qs = Category.objects.filter(user=user, name__iexact=value.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "You already have a category with this name."
            )
        return value.strip()
class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name", read_only=True
    )
    class Meta:
        model = Expense
        fields = [
            "id", "title", "category", "category_name", "amount",
            "expense_date", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at", "category_name"]
    def validate_category(self, category):
        if category.user_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                "Select one of your own categories."
            )
        return category
class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name", read_only=True
    )
    spent_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    warning = serializers.CharField(read_only=True)
    class Meta:
        model = Budget
        fields = [
            "id", "category", "category_name", "month", "limit_amount",
            "spent_amount", "remaining_amount", "warning",
        ]
        read_only_fields = [
            "id", "category_name", "spent_amount",
            "remaining_amount", "warning",
        ]
    def validate_category(self, category):
        if category.user_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                "Select one of your own categories."
            )
        return category
    def validate_month(self, value):
        if value.day != 1:
            raise serializers.ValidationError(
                "month must be the first day of the month, e.g. 2026-10-01."
            )
        return value
class RecurringExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name", read_only=True
    )
    class Meta:
        model = RecurringExpense
        fields = [
            "id", "category", "category_name", "title", "amount",
            "frequency", "start_date", "next_run_date", "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
    def validate_category(self, category):
        if category.user_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                "Select one of your own categories."
            )
        return category
    def validate(self, attrs):
        start = attrs.get("start_date",
                          getattr(self.instance, "start_date", None))
        next_run = attrs.get("next_run_date",
                             getattr(self.instance, "next_run_date", None))
        if start and next_run and next_run < start:
            raise serializers.ValidationError({
                "next_run_date": "Next run date cannot be before start date."
            })
        return attrs