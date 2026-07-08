from django.urls import path

from . import views

app_name = "garage"

urlpatterns = [
    path("", views.garage, name="garage"),
    path("cars/add/", views.add_car, name="add_car"),
    path("cars/<int:pk>/", views.car_detail, name="car_detail"),
    path("cars/<int:pk>/maintenance/add/", views.add_maintenance, name="add_maintenance"),
    path("maintenance/<int:pk>/edit/", views.edit_maintenance, name="edit_maintenance"),
]
