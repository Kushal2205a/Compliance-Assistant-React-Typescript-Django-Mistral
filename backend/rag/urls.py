from django.urls import path
from .views import viewQueryPDF, viewQueryPDFStream

urlpatterns = [
    path("query/" , viewQueryPDF.as_view(), name= "query"),
    path("query/stream/" , viewQueryPDFStream.as_view(), name= "query_stream"),
]