from django.urls import path
from .views import (
    CategoryListCreateView, CategoryDetailView,
    ExpenseListCreateView, ExpenseDetailView,
    BudgetListCreateView, BudgetDetailView,
    RecurringExpenseListCreateView, RecurringExpenseDetailView,
    MonthlyReportView, CategorySummaryView, TopExpensesView,
    ExpenseCSVExportView,
)
urlpatterns = [
    path("categories/", CategoryListCreateView.as_view()),
    path("categories/<int:pk>/", CategoryDetailView.as_view()),
    path("expenses/", ExpenseListCreateView.as_view()),
    path("expenses/<int:pk>/", ExpenseDetailView.as_view()),
    path("expenses/export-csv/", ExpenseCSVExportView.as_view()),
    path("budgets/", BudgetListCreateView.as_view()),
    path("budgets/<int:pk>/", BudgetDetailView.as_view()),
    path("recurring-expenses/", RecurringExpenseListCreateView.as_view()),
    path("recurring-expenses/<int:pk>/",
         RecurringExpenseDetailView.as_view()),
    path("reports/monthly/", MonthlyReportView.as_view()),
    path("reports/categories/", CategorySummaryView.as_view()),
    path("reports/top-expenses/", TopExpensesView.as_view()),
]
