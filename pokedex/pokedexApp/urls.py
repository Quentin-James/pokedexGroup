from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='index'),
    # route courte pour accéder au détail via '/1'
    path('<int:pokemon_id>/', views.pokemon, name='pokemon_detail'),
    # route longue déjà présente (conserve la compatibilité)
    path('pokemon/<int:pokemon_id>/', views.pokemon, name='pokemon_detail'),
    # page de formation
    path('formation/', views.formation, name='formation'),
]