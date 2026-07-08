from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CarForm, MaintenanceRecordForm
from .models import Car, MaintenanceRecord


def register(request):
    if request.user.is_authenticated:
        return redirect("garage:garage")
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("garage:garage")
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def garage(request):
    cars = request.user.cars.all()
    return render(request, "garage/garage.html", {"cars": cars})


@login_required
def add_car(request):
    if request.method == "POST":
        form = CarForm(request.POST)
        if form.is_valid():
            car = form.save(commit=False)
            car.owner = request.user
            car.save()
            return redirect(car)
    else:
        form = CarForm()
    return render(request, "garage/car_form.html", {"form": form})


@login_required
def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk, owner=request.user)
    records = car.maintenance_records.all()
    return render(
        request,
        "garage/car_detail.html",
        {"car": car, "records": records},
    )


@login_required
def add_maintenance(request, pk):
    car = get_object_or_404(Car, pk=pk, owner=request.user)
    if request.method == "POST":
        form = MaintenanceRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.car = car
            record.save()
            return redirect(car)
    else:
        form = MaintenanceRecordForm()
    return render(
        request,
        "garage/maintenance_form.html",
        {"form": form, "car": car},
    )


@login_required
def edit_maintenance(request, pk):
    record = get_object_or_404(
        MaintenanceRecord, pk=pk, car__owner=request.user
    )
    if request.method == "POST":
        form = MaintenanceRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            return redirect(record.car)
    else:
        form = MaintenanceRecordForm(instance=record)
    return render(
        request,
        "garage/maintenance_form.html",
        {"form": form, "car": record.car, "record": record},
    )
