"""
A module for loading contexts using context hints.
"""
from collection import defaultdict

from django.db.models.loading import get_model


# Get the querysets for each model. The context hints are needed for
# this.
#
# input: [cr.context_hints for cr in context_renderers]
# querysets = {
#    model: queryset,
# }
def get_querysets_for_context_hints(context_hints_list):
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
    for context_hints in context_hints_list:
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


# Get the ids of each model that will need to be fetched. The context
# and context hints will need to be provided for this
#
# models_to_fetch = {
#   model: id_list,
# }

# Fetch the models for each ID and return them in a dictionary keyed on
# the model
#
# fetched_model_data = {
#   model: {
#     id: obj,
#   },
# }

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
