from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Car, MaintenanceRecord

User = get_user_model()


class GarageTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw12345!")
        self.bob = User.objects.create_user("bob", password="pw12345!")
        self.car = Car.objects.create(owner=self.alice, year=2018, make="Honda", model="Civic")

    def test_garage_requires_login(self):
        resp = self.client.get(reverse("garage:garage"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_garage_shows_only_own_cars(self):
        Car.objects.create(owner=self.bob, year=2020, make="Toyota", model="Corolla")
        self.client.force_login(self.alice)
        resp = self.client.get(reverse("garage:garage"))
        self.assertContains(resp, "Honda")
        self.assertNotContains(resp, "Corolla")

    def test_cannot_view_another_users_car(self):
        self.client.force_login(self.bob)
        resp = self.client.get(reverse("garage:car_detail", args=[self.car.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_add_car(self):
        self.client.force_login(self.alice)
        resp = self.client.post(
            reverse("garage:add_car"),
            {"year": 2022, "make": "Mazda", "model": "3", "nickname": ""},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Car.objects.filter(owner=self.alice, make="Mazda").exists())

    def test_add_maintenance(self):
        self.client.force_login(self.alice)
        resp = self.client.post(
            reverse("garage:add_maintenance", args=[self.car.pk]),
            {"description": "Oil change", "mileage": 45000, "performed_on": "2026-06-01"},
        )
        self.assertEqual(resp.status_code, 302)
        record = MaintenanceRecord.objects.get(car=self.car)
        self.assertEqual(record.mileage, 45000)
        self.assertEqual(self.car.current_mileage, 45000)

    def test_register_creates_user_and_logs_in(self):
        resp = self.client.post(
            reverse("register"),
            {"username": "carol", "password1": "sup3rsecret!", "password2": "sup3rsecret!"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username="carol").exists())
        # New user is logged in and lands on their (empty) garage.
        garage_resp = self.client.get(reverse("garage:garage"))
        self.assertEqual(garage_resp.status_code, 200)

    def test_register_rejects_mismatched_passwords(self):
        resp = self.client.post(
            reverse("register"),
            {"username": "dave", "password1": "sup3rsecret!", "password2": "different!"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="dave").exists())

    def test_cannot_add_maintenance_to_another_users_car(self):
        self.client.force_login(self.bob)
        resp = self.client.post(
            reverse("garage:add_maintenance", args=[self.car.pk]),
            {"description": "Hack", "mileage": 1, "performed_on": "2026-06-01"},
        )
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(MaintenanceRecord.objects.filter(car=self.car).exists())

    def test_edit_maintenance(self):
        record = MaintenanceRecord.objects.create(
            car=self.car, description="Oil change", mileage=45000, performed_on="2026-06-01"
        )
        self.client.force_login(self.alice)
        resp = self.client.post(
            reverse("garage:edit_maintenance", args=[record.pk]),
            {"description": "Oil change + filter", "mileage": 45200, "performed_on": "2026-06-02"},
        )
        self.assertEqual(resp.status_code, 302)
        record.refresh_from_db()
        self.assertEqual(record.description, "Oil change + filter")
        self.assertEqual(record.mileage, 45200)

    def test_cannot_edit_another_users_maintenance(self):
        record = MaintenanceRecord.objects.create(
            car=self.car, description="Oil change", mileage=45000, performed_on="2026-06-01"
        )
        self.client.force_login(self.bob)
        resp = self.client.post(
            reverse("garage:edit_maintenance", args=[record.pk]),
            {"description": "Hacked", "mileage": 1, "performed_on": "2026-06-01"},
        )
        self.assertEqual(resp.status_code, 404)
        record.refresh_from_db()
        self.assertEqual(record.description, "Oil change")
