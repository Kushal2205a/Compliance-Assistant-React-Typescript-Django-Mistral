from django.urls import path
from .views import viewQueryPDF

urlpatterns = [
    path("query/" , viewQueryPDF.as_view(), name= "query")
]