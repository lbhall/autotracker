from django.conf import settings
from django.db import models
from django.urls import reverse


class Car(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cars",
    )
    year = models.PositiveIntegerField()
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    nickname = models.CharField(max_length=100, blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "year", "make", "model"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.nickname:
            return self.nickname
        return f"{self.year} {self.make} {self.model}"

    @property
    def current_mileage(self):
        latest = self.maintenance_records.first()
        return latest.mileage if latest else None

    def get_absolute_url(self):
        return reverse("garage:car_detail", args=[self.pk])


class MaintenanceRecord(models.Model):
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="maintenance_records",
    )
    description = models.TextField()
    mileage = models.PositiveIntegerField(help_text="Mileage when the service was performed")
    performed_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-mileage", "-performed_on"]

    def __str__(self):
        return f"{self.description[:40]} @ {self.mileage} mi"
