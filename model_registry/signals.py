import django.dispatch

class_registered = django.dispatch.Signal(providing_args=["cls"])