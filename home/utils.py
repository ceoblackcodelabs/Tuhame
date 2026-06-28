# apps/home/utils.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import IntegrityError
from .models import SavedProperty
from properties.models import Property
import json


@login_required
@require_POST
def toggle_save_property(request):
    """
    AJAX view to toggle save/un-save a property
    """
    try:
        data = json.loads(request.body)
        property_id = data.get('property_id')
        action = data.get('action', 'toggle')

        if not property_id:
            return JsonResponse({
                'success': False,
                'error': 'Property ID is required'
            }, status=400)

        # Get the property
        try:
            property_obj = Property.objects.get(id=property_id, is_active=True)
        except Property.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Property not found'
            }, status=404)

        # Check if already saved
        saved_entry = SavedProperty.objects.filter(
            user=request.user,
            property=property_obj
        ).first()

        if action == 'save':
            if saved_entry:
                return JsonResponse({
                    'success': True,
                    'action': 'already_saved',
                    'message': 'Property already saved',
                    'saved': True,
                    'count': request.user.saved_properties.count()
                })
            else:
                try:
                    SavedProperty.objects.create(user=request.user, property=property_obj)
                    return JsonResponse({
                        'success': True,
                        'action': 'saved',
                        'message': f'"{property_obj.title}" saved to favourites!',
                        'saved': True,
                        'count': request.user.saved_properties.count()
                    })
                except IntegrityError:
                    return JsonResponse({
                        'success': True,
                        'action': 'already_saved',
                        'message': 'Property already saved',
                        'saved': True,
                        'count': request.user.saved_properties.count()
                    })

        elif action == 'unsave':
            if saved_entry:
                saved_entry.delete()
                return JsonResponse({
                    'success': True,
                    'action': 'unsaved',
                    'message': f'"{property_obj.title}" removed from favourites.',
                    'saved': False,
                    'count': request.user.saved_properties.count()
                })
            else:
                return JsonResponse({
                    'success': True,
                    'action': 'not_saved',
                    'message': 'Property was not saved',
                    'saved': False,
                    'count': request.user.saved_properties.count()
                })

        else:  # toggle
            if saved_entry:
                saved_entry.delete()
                return JsonResponse({
                    'success': True,
                    'action': 'unsaved',
                    'message': f'"{property_obj.title}" removed from favourites.',
                    'saved': False,
                    'count': request.user.saved_properties.count()
                })
            else:
                try:
                    SavedProperty.objects.create(user=request.user, property=property_obj)
                    return JsonResponse({
                        'success': True,
                        'action': 'saved',
                        'message': f'"{property_obj.title}" saved to favourites!',
                        'saved': True,
                        'count': request.user.saved_properties.count()
                    })
                except IntegrityError:
                    return JsonResponse({
                        'success': True,
                        'action': 'already_saved',
                        'message': 'Property already saved',
                        'saved': True,
                        'count': request.user.saved_properties.count()
                    })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def get_saved_properties(request):
    """
    Get all saved properties for the current user
    """
    saved = request.user.saved_properties.select_related('property').all()

    properties_data = []
    for item in saved:
        prop = item.property
        properties_data.append({
            'id': prop.id,
            'title': prop.title,
            'slug': prop.slug,
            'price': float(prop.price),
            'city': prop.city,
            'state': prop.state,
            'property_type': prop.get_property_type_display(),
            'bedrooms': prop.bedrooms,
            'bathrooms': float(prop.bathrooms),
            'area_sqft': float(prop.area_sqft),
            'main_image': prop.main_image.url if prop.main_image else None,
            'saved_at': item.saved_at.isoformat()
        })

    return JsonResponse({
        'success': True,
        'count': len(properties_data),
        'properties': properties_data
    })

@login_required
def check_saved_status(request):
    """
    Check if a property is saved by the current user
    """
    property_id = request.GET.get('property_id')

    if not property_id:
        return JsonResponse({
            'success': False,
            'error': 'Property ID is required'
        }, status=400)

    try:
        is_saved = SavedProperty.objects.filter(
            user=request.user,
            property_id=property_id
        ).exists()

        return JsonResponse({
            'success': True,
            'saved': is_saved,
            'property_id': property_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)