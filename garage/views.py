import json

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Max
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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
            # Append new cars to the end of the current ordering.
            next_position = request.user.cars.aggregate(m=Max("position"))["m"]
            car.position = (next_position or 0) + 1
            car.save()
            return redirect(car)
    else:
        form = CarForm()
    return render(request, "garage/car_form.html", {"form": form})


@login_required
@require_POST
def reorder_cars(request):
    try:
        order = json.loads(request.body)["order"]
        ordered_ids = [int(pk) for pk in order]
    except (ValueError, KeyError, TypeError):
        return HttpResponseBadRequest("Invalid payload")

    # Only reorder cars the user actually owns.
    owned_ids = set(request.user.cars.values_list("id", flat=True))
    if set(ordered_ids) != owned_ids:
        return HttpResponseBadRequest("Order must reference all of your cars exactly once")

    cars_by_id = request.user.cars.in_bulk(ordered_ids)
    for position, pk in enumerate(ordered_ids):
        cars_by_id[pk].position = position
    Car.objects.bulk_update(cars_by_id.values(), ["position"])
    return JsonResponse({"status": "ok"})


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
