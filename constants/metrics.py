from enum import Enum

class ConsumptionTags(Enum):
    DOMESTIC_COLD_WATER = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_COLD_WATER"
    DOMESTIC_ENERGY_GENERAL = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_ENERGY_GENERAL"
    DOMESTIC_HOT_WATER = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_HOT_WATER"
    DOMESTIC_WATER_GENERAL = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_DOMESTIC_WATER_GENERAL"
    PEOPLE_FLOW_IN = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_IN"
    PEOPLE_FLOW_OUT = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_PEOPLE_FLOW_OUT"
    THERMAL_ENERGY_COOLING = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_COOLING"
    THERMAL_ENERGY_HEAT = "_TRANSVERSAL_CONSUMPTION_LIST_TAG_NAME_THERMAL_ENERGY_HEAT"

# Mapping of tags to readable names
CONSUMPTION_TAGS_MAPPING = {
    ConsumptionTags.DOMESTIC_COLD_WATER.value: "Agua fría sanitaria",
    ConsumptionTags.DOMESTIC_ENERGY_GENERAL.value: "Energía general",
    ConsumptionTags.DOMESTIC_HOT_WATER.value: "Agua caliente sanitaria",
    ConsumptionTags.DOMESTIC_WATER_GENERAL.value: "Agua general",
    ConsumptionTags.PEOPLE_FLOW_IN.value: "Flujo entrante de personas",
    ConsumptionTags.PEOPLE_FLOW_OUT.value: "Flujo saliente de personas",
    ConsumptionTags.THERMAL_ENERGY_COOLING.value: "Energía térmica frío",
    ConsumptionTags.THERMAL_ENERGY_HEAT.value: "Energía térmica calor"
}

# Mapping for consumption types
CONSUMPTION_TYPE_MAP = {
    "Energía térmica calor": ConsumptionTags.THERMAL_ENERGY_HEAT.value,
    "Energía térmica frío": ConsumptionTags.THERMAL_ENERGY_COOLING.value,
    "Agua fría": ConsumptionTags.DOMESTIC_COLD_WATER.value,
    "Agua caliente": ConsumptionTags.DOMESTIC_HOT_WATER.value,
    "Agua caliente sanitaria": ConsumptionTags.DOMESTIC_HOT_WATER.value,
    "Agua general": ConsumptionTags.DOMESTIC_WATER_GENERAL.value,
    "Energía general": ConsumptionTags.DOMESTIC_ENERGY_GENERAL.value,
    "Flujo de personas entrada": ConsumptionTags.PEOPLE_FLOW_IN.value,
    "Flujo de personas salida": ConsumptionTags.PEOPLE_FLOW_OUT.value
}
