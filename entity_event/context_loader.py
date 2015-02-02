"""
A module for loading contexts using context hints.
"""
from collection import defaultdict

from django.db.models.loading import get_model
from manager_utils import id_dict


# Get the querysets for each model. The context hints are needed for
# this.
#
# input: [cr.context_hints for cr in context_renderers]
# querysets = {
#    model: queryset,
# }
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
            model_select_relateds[model].union(hints.get('select_related', []))
            model_prefetch_relateds[model].union(hints.get('prefetch_related', []))

    # Attach select and prefetch related parameters to the querysets if needed
    for model, queryset in model_querysets.items():
        if model_select_relateds[model]:
            model_querysets[model] = queryset.select_related(*model_select_relateds[model])
        if model_prefetch_relateds[model]:
            model_querysets[model] = queryset.prefetch_related(*model_prefetch_relateds[model])

    return model_querysets


def dict_find(d, which_key):
    """
    Finds key values in a nested dictionary
    """
    for k, v in d.iteritems():
        if k == which_key:
            for value in v if isinstance(v, list) else [v]:
                yield value
        elif isinstance(v, dict):
            for result in dict_find(v, which_key):
                yield result
        elif isinstance(v, list):
            for i in v:
                for result in dict_find(i, which_key):
                    yield result


# Get the ids of each model that will need to be fetched. The context
# and context hints will need to be provided for this
#
# model_ids_to_fetch = {
#   model: id_set,
# }
def get_model_ids_to_fetch(events, context_hints_per_source):
    """
    Obtains the ids of all models that need to be fetched. Returns a dictionary of models that
    point to sets of ids that need to be fetched. Return output is as follows:

    {
        model: [id1, id2, ...],
        ...
    }
    """
    model_ids_to_fetch = defaultdict(set)

    for event in events:
        context_hints = context_hints_per_source[event.source]
        for context_key, hints in context_hints.items():
            model_ids_to_fetch[get_model(hints['app_name'], hints['model_name'])].union(
                v for v in dict_find(event.context, context_key)
            )


# Fetch the models for each ID and return them in a dictionary keyed on
# the model
#
# fetched_model_data = {
#   model: {
#     id: obj,
#   },
# }
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


# Group each source by the objects that need to be populated in the context
#
# source_context_key_models = {
#   (source, key): model,
# }

# Load the contexts. Needs the fetched_model_data and source_context_key_models
#
# for e in events:
#  for key in e.context:
#   if (e.source, key) in source_context_key_models:
#    e.context[key] = fetch_model_data[(e.source, key)][e.context[key]]
