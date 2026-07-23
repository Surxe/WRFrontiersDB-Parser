# 1. Map: Module-level short_key -> ModuleStat ID
# Used when the stat key used in Module levels does not match ModuleStat.short_key 1-to-1.
# Developer guidance: If a newly added stat short_key relates to an existing ModuleStat, add the mapping here.
STAT_KEY_TO_MODULE_STAT_ID: dict[str, str] = {
    "ChargeDuration":       "DA_ModuleStat_ChargeDrain.0",
    "Cooldown":             "DA_ModuleStat_Cooldown.0",
    "ShieldRegeneration":   "DA_ModuleStat_ShieldRegeneration.0",
    "TimeToReload":         "DA_ModuleStat_ReloadingTime.0",
    "DamageArmor":          "DA_ModuleStat_ArmorDamage.0",
    "RoundsPerMinute":      "DA_ModuleStat_FireRate.0",
    "FuelCapacity":         "DA_ModuleStat_FuelCapacity.0",
    "ShieldAmount":         "DA_ModuleStat_ShieldAmount.0",
    "ShieldDelayReduction": "DA_ModuleStat_ShieldDelayReduction.0",
    "Armor":                "DA_ModuleStat_Armor.0",
    "DamageNoArmor":        "DA_ModuleStat_ShieldDamage.0",
    "Mobility":             "DA_ModuleStat_Acceleration.0",
}

# 2. Map: Module-level short_key -> more_is_better (bool)
# Used ONLY for stats that do not have a ModuleStat in game data (neither 1-to-1 nor in STAT_KEY_TO_MODULE_STAT_ID).
# Synthetic ModuleStats will be created for these with ID "DA_ModuleStat_Synthetic_<short_key>".
# Developer guidance: If a newly added stat short_key cannot be related to an existing ModuleStat, add its more_is_better setting here.
SYNTHETIC_STAT_MORE_IS_BETTER: dict[str, bool] = {
    "AoeArmor":              True,
    "AoeNoArmor":            True,
    "TimeBetweenShots":      True,
    "RechargeDelay":         False,
    "RechargeTime":          False,
    "DelayAndRechargeTotal": False,
}
