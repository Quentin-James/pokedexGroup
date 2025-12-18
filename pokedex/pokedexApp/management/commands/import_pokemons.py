from django.core.management.base import BaseCommand
from pokedexApp.pokeapi import fetch_and_create_pokemon
from pokedexApp.models import pokemon as PokemonModel

class Command(BaseCommand):
    help = 'Import pokemons from PokeAPI. Usage: import_pokemons start end'

    def add_arguments(self, parser):
        parser.add_argument('start', type=int, help='Start ID')
        parser.add_argument('end', type=int, nargs='?', help='End ID (inclusive)', default=None)

    def handle(self, *args, **options):
        start = options['start']
        end = options['end'] if options['end'] is not None else start
        if start > end:
            start, end = end, start
        for pid in range(start, end+1):
            self.stdout.write(f'Fetching pokemon {pid}...')
            obj = fetch_and_create_pokemon(pid, PokemonModel)
            if obj:
                self.stdout.write(self.style.SUCCESS(f'Imported {obj.name} ({obj.pk})'))
            else:
                self.stdout.write(self.style.WARNING(f'Failed to import {pid}'))

