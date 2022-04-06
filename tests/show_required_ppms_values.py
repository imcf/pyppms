#!/usr/bin/env python3

"""Script to print the settings required in your PPMS test instance."""

from ppms_values import values


ppms_values = values()

print("\nThe following objects are required in your PPMS test-instance:\n")
print("(NOTE: default values are mostly skipped here)\n\n")

skipdefaults = [
    "unitbcode",
    "Autonomy Required",
    "Autonomy Required After Hours",
    "Stats",
    "Schedules",
    "Bookable",
    "Core facility ref",
    "System id",
    "mustchbcode",
    "mustchpwd",
    "affiliation",
    "bcode",
]

for ppms_type in ppms_values.keys():
    print(f"#################### {ppms_type} ####################")
    for key, val in ppms_values[ppms_type].items():
        if key in skipdefaults:
            continue
        print(f"  {key} -> {val}")
    print("\n")
