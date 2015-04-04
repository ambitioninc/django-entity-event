"""
A module for loading contexts using context hints.
"""
from collections import defaultdict
import six

from django.conf import settings
from django.db.models import Q
from django.db.models.loading import get_model
from manager_utils import id_dict

from entity_event.models import ContextRenderer


def get_context_hints_per_source(context_renderers):
    """
    Given a list of context renderers, return a dictionary of context hints per source.
    """
    # Merge the context render hints for each source as there can be multiple context hints for
    # sources depending on the render target. Merging them together involves combining select
    # and prefetch related hints for each context renderer
    context_hints_per_source = defaultdict(lambda: defaultdict(lambda: {
        'app_name': None,
        'model_name': None,
        'select_related': set(),
        'prefetch_related': set(),
    }))
    for cr in context_renderers:
        for key, hints in cr.context_hints.items() if cr.context_hints else []:
            for source in cr.get_sources():
                context_hints_per_source[source][key]['app_name'] = hints['app_name']
                context_hints_per_source[source][key]['model_name'] = hints['model_name']
                context_hints_per_source[source][key]['select_related'].update(hints.get('select_related', []))
                context_hints_per_source[source][key]['prefetch_related'].update(hints.get('prefetch_related', []))

    return context_hints_per_source


def get_querysets_for_context_hints(context_hints_per_source):
    """
    Given a list of context hint dictionaries, return a dictionary
    of querysets for efficient context loading. The return value
    is structured as follows:

    {
        model: queryset,
        ...
    }
    """
    model_select_relateds = defaultdict(set)
    model_prefetch_relateds = defaultdict(set)
    model_querysets = {}
    for context_hints in context_hints_per_source.values():
        for hints in context_hints.values():
            model = get_model(hints['app_name'], hints['model_name'])
            model_querysets[model] = model.objects
            model_select_relateds[model].update(hints.get('select_related', []))
            model_prefetch_relateds[model].update(hints.get('prefetch_related', []))

    # Attach select and prefetch related parameters to the querysets if needed
    for model, queryset in model_querysets.items():
        if model_select_relateds[model]:
            queryset = queryset.select_related(*model_select_relateds[model])
        if model_prefetch_relateds[model]:
            queryset = queryset.prefetch_related(*model_prefetch_relateds[model])
        model_querysets[model] = queryset

    return model_querysets


def dict_find(d, which_key):
    """
    Finds key values in a nested dictionary. Returns a tuple of the dictionary in which
    the key was found along with the value
    """
    # If the starting point is a list, iterate recursively over all values
    if isinstance(d, (list, tuple)):
        for i in d:
            for result in dict_find(i, which_key):
                yield result

    # Else, iterate over all key values of the dictionary
    elif isinstance(d, dict):
        for k, v in d.items():
            if k == which_key:
                yield d, v
            for result in dict_find(v, which_key):
                yield result


def get_model_ids_to_fetch(events, context_hints_per_source):
    """
    Obtains the ids of all models that need to be fetched. Returns a dictionary of models that
    point to sets of ids that need to be fetched. Return output is as follows:

    {
        model: [id1, id2, ...],
        ...
    }
    """
    number_types = (complex, float) + six.integer_types
    model_ids_to_fetch = defaultdict(set)

    for event in events:
        context_hints = context_hints_per_source.get(event.source, {})
        for context_key, hints in context_hints.items():
            for d, value in dict_find(event.context, context_key):
                values = value if isinstance(value, list) else [value]
                model_ids_to_fetch[get_model(hints['app_name'], hints['model_name'])].update(
                    v for v in values if isinstance(v, number_types)
                )

    return model_ids_to_fetch


def fetch_model_data(model_querysets, model_ids_to_fetch):
    """
    Given a dictionary of models to querysets and model IDs to models, fetch the IDs
    for every model and return the objects in the following structure.

    {
        model: {
            id: obj,
            ...
        },
        ...
    }
    """
    return {
        model: id_dict(model_querysets[model].filter(id__in=ids_to_fetch))
        for model, ids_to_fetch in model_ids_to_fetch.items()
    }


def load_fetched_objects_into_contexts(events, model_data, context_hints_per_source):
    """
    Given the fetched model data and the context hints for each source, go through each
    event and populate the contexts with the loaded information.
    """
    for event in events:
        context_hints = context_hints_per_source.get(event.source, {})
        for context_key, hints in context_hints.items():
            model = get_model(hints['app_name'], hints['model_name'])
            for d, value in dict_find(event.context, context_key):
                if isinstance(value, list):
                    for i, model_id in enumerate(d[context_key]):
                        d[context_key][i] = model_data[model].get(model_id)
                else:
                    d[context_key] = model_data[model].get(value)


def load_renderers_into_events(events, mediums, context_renderers, default_rendering_style):
    """
    Given the events and the context renderers, load the renderers into the event objects
    so that they may be able to call the 'render' method later on.
    """
    # Make a mapping of source groups and rendering styles to context renderers. Do
    # the same for sources and rendering styles to context renderers
    source_group_style_to_renderer = {
        (cr.source_group_id, cr.rendering_style_id): cr
        for cr in context_renderers if cr.source_group_id
    }
    source_style_to_renderer = {
        (cr.source_id, cr.rendering_style_id): cr
        for cr in context_renderers if cr.source_id
    }

    for e in events:
        for m in mediums:
            # Try the following when loading a context renderer for a medium in an event.
            # 1. Try to look up the renderer based on the source group and medium rendering style
            # 2. If step 1 doesn't work, look up based on the source and medium rendering style
            # 3. If step 2 doesn't work, look up based on the source group and default rendering style
            # 4. if step 3 doesn't work, look up based on the source and default rendering style
            # If none of those steps work, this event will not be able to be rendered for the mediun
            cr = source_group_style_to_renderer.get((e.source.group_id, m.rendering_style_id))
            if not cr:
                cr = source_style_to_renderer.get((e.source_id, m.rendering_style_id))
            if not cr and default_rendering_style:
                cr = source_group_style_to_renderer.get((e.source.group_id, default_rendering_style.id))
            if not cr and default_rendering_style:
                cr = source_style_to_renderer.get((e.source_id, default_rendering_style.id))

            if cr:
                e._context_renderers[m] = cr


def get_default_rendering_style():
    default_rendering_style = getattr(settings, 'DEFAULT_ENTITY_EVENT_RENDERING_STYLE', None)
    if default_rendering_style:
        default_rendering_style = get_model('entity_event', 'RenderingStyle').objects.get(name=default_rendering_style)

    return default_rendering_style


def load_contexts_and_renderers(events, mediums):
    """
    Given a list of events and mediums, load the context model data into the contexts of the events.
    """
    sources = {event.source for event in events}
    rendering_styles = {medium.rendering_style for medium in mediums if medium.rendering_style}

    # Fetch the default rendering style and add it to the set of rendering styles
    default_rendering_style = get_default_rendering_style()
    if default_rendering_style:
        rendering_styles.add(default_rendering_style)

    context_renderers = ContextRenderer.objects.filter(
        Q(source__in=sources, rendering_style__in=rendering_styles) |
        Q(source_group_id__in=[s.group_id for s in sources], rendering_style__in=rendering_styles)).select_related(
            'source', 'rendering_style').prefetch_related('source_group__source_set')

    context_hints_per_source = get_context_hints_per_source(context_renderers)
    model_querysets = get_querysets_for_context_hints(context_hints_per_source)
    model_ids_to_fetch = get_model_ids_to_fetch(events, context_hints_per_source)
    model_data = fetch_model_data(model_querysets, model_ids_to_fetch)
    load_fetched_objects_into_contexts(events, model_data, context_hints_per_source)
    load_renderers_into_events(events, mediums, context_renderers, default_rendering_style)

    return events
