from django.shortcuts import render

# Create your views here.
import csv
from datetime import date
from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Category, Expense, Budget, RecurringExpense
from .serializers import (
    CategorySerializer, ExpenseSerializer,
    BudgetSerializer, RecurringExpenseSerializer,
)
class OwnedQuerysetMixin:
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    ordering_fields = ["expense_date", "amount", "created_at"]
    ordering = ["-expense_date", "-id"]
    def get_queryset(self):
        qs = Expense.objects.filter(user=self.request.user).select_related(
            "category"
        )
        params = self.request.query_params
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        category = params.get("category")
        min_amount = params.get("min_amount")
        max_amount = params.get("max_amount")
        try:
            if date_from:
                qs = qs.filter(expense_date__gte=date.fromisoformat(date_from))
            if date_to:
                qs = qs.filter(expense_date__lte=date.fromisoformat(date_to))
            if category:
                qs = qs.filter(category_id=int(category))
            if min_amount:
                qs = qs.filter(amount__gte=Decimal(min_amount))
            if max_amount:
                qs = qs.filter(amount__lte=Decimal(max_amount))
        except (ValueError, TypeError):
            raise ValidationError({
                "filters": [
                    "Use valid dates (YYYY-MM-DD), category ID and amounts."
                ]
            })
        if date_from and date_to and date_from > date_to:
            raise ValidationError({
                "date_range": ["date_from cannot be after date_to."]
            })
        if min_amount and max_amount and Decimal(min_amount) > Decimal(max_amount):
            raise ValidationError({
                "amount_range": ["min_amount cannot exceed max_amount."]
            })
        return qs
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseSerializer
    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user).select_related(
            "category"
        )
class BudgetListCreateView(generics.ListCreateAPIView):
    serializer_class = BudgetSerializer
    def get_queryset(self):
        qs = Budget.objects.filter(user=self.request.user).select_related(
            "category"
        )
        month = self.request.query_params.get("month")
        if month:
            try:
                month_date = date.fromisoformat(month)
                qs = qs.filter(month=month_date.replace(day=1))
            except ValueError:
                raise ValidationError({"month": ["Use YYYY-MM-DD."]})
        return qs
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if self.request.method == "GET":
            for item in serializer.instance if isinstance(
                serializer.instance, (list, tuple)
            ) else []:
                pass
        return serializer
    def list(self, request, *args, **kwargs):
        budgets = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(budgets)
        rows = page if page is not None else budgets
        data = []
        for budget in rows:
            data.append(self.budget_with_spending(budget))
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)
    def budget_with_spending(self, budget):
        month_start = budget.month
        if month_start.month == 12:
            next_month = date(month_start.year + 1, 1, 1)
        else:
            next_month = date(month_start.year, month_start.month + 1, 1)
        spent = Expense.objects.filter(
            user=self.request.user,
            category=budget.category,
            expense_date__gte=month_start,
            expense_date__lt=next_month,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        ratio = spent / budget.limit_amount
        if ratio >= Decimal("1"):
            warning = "over_100"
        elif ratio >= Decimal("0.80"):
            warning = "over_80"
        else:
            warning = "normal"
        return {
            "id": budget.id,
            "category": budget.category_id,
            "category_name": budget.category.name,
            "month": budget.month,
            "limit_amount": budget.limit_amount,
            "spent_amount": spent,
            "remaining_amount": budget.limit_amount - spent,
            "warning": warning,
        }
class BudgetDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BudgetSerializer
    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
class RecurringExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = RecurringExpenseSerializer
    def get_queryset(self):
        return RecurringExpense.objects.filter(
            user=self.request.user
        ).select_related("category")
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
class RecurringExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RecurringExpenseSerializer
    def get_queryset(self):
        return RecurringExpense.objects.filter(user=self.request.user)
class MonthlyReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        try:
            year = int(request.query_params.get("year", date.today().year))
        except ValueError:
            raise ValidationError({"year": ["Provide a valid year."]})
        rows = (
            Expense.objects.filter(
                user=request.user, expense_date__year=year
            )
            .annotate(month=TruncMonth("expense_date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        totals = {row["month"].month: row["total"] for row in rows}
        return Response({
            "year": year,
            "monthly_totals": [
                {"month": month, "total": totals.get(month, Decimal("0.00"))}
                for month in range(1, 13)
            ],
        })
class CategorySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        try:
            year = int(request.query_params.get("year", date.today().year))
            month = int(request.query_params.get("month", date.today().month))
            if month not in range(1, 13):
                raise ValueError
        except ValueError:
            raise ValidationError({
                "period": ["Provide a valid year and month (1 to 12)."]
            })
        rows = (
            Expense.objects.filter(
                user=request.user,
                expense_date__year=year,
                expense_date__month=month,
            )
            .values("category_id", "category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        grand_total = sum((row["total"] for row in rows), Decimal("0.00"))
        results = []
        for row in rows:
            percentage = (
                (row["total"] / grand_total * 100)
                if grand_total else Decimal("0")
            )
            results.append({
                "category_id": row["category_id"],
                "category": row["category__name"],
                "total": row["total"],
                "percentage": round(percentage, 2),
            })
        return Response({
            "year": year, "month": month,
            "grand_total": grand_total, "categories": results,
        })
class TopExpensesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        qs = (
            Expense.objects.filter(user=request.user)
            .select_related("category")
            .order_by("-amount", "-expense_date")[:5]
        )
        return Response(ExpenseSerializer(
            qs, many=True, context={"request": request}
        ).data)
class ExpenseCSVExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        # Reuse exactly the same filters as the expense list.
        view = ExpenseListCreateView()
        view.request = request
        view.args = ()
        view.kwargs = {}
        qs = view.get_queryset()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="expenses.csv"'
        )
        writer = csv.writer(response)
        writer.writerow([
            "ID", "Title", "Category", "Amount",
            "Expense date", "Notes"
        ])
        for expense in qs:
            writer.writerow([
                expense.id, expense.title, expense.category.name,
                expense.amount, expense.expense_date, expense.notes
            ])
        return response