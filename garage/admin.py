from django.contrib import admin

from .models import Car, MaintenanceRecord


class MaintenanceRecordInline(admin.TabularInline):
    model = MaintenanceRecord
    extra = 0


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("display_name", "owner", "year", "make", "model")
    list_filter = ("owner", "make")
    search_fields = ("make", "model", "nickname")
    inlines = [MaintenanceRecordInline]


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ("car", "description", "mileage", "performed_on")
    list_filter = ("car",)
