# Dashboard and backend for UCF TransLoc Shuttles
# Install
1. Add bus.py within the config directory
2. Add to configuration.yaml
```
command_line:
  - sensor:
      name: "UCF Bus Tracker"
      unique_id: ucf_bus_tracker_main
      scan_interval: 60
      command: "python3 /config/bus.py"
      value_template: "{{ value_json.next_minutes if value_json.next_minutes is not none else 'Unknown' }}"
      json_attributes:
        - stops
        - stop
        - error
```
3. Restart Home Assistant

# Dashboard Widgets
## Markdown Card
```yaml
type: markdown
content: >
  {% for route in ["Pegasus Express", "Knights Express"] %}

  {% set stops = state_attr('sensor.ucf_bus_tracker', 'stops') %}

  {% if stops %}

  {% set etas = stops[0].etas | selectattr('route', 'eq', route) |
  map(attribute='minutes') | list %}

  | **{{ route }}** | {{ etas[0] ~ ' min' if etas[0] is defined else '--' }} |
  <font color="grey">{{ etas[1] ~ ' min' if etas[1] is defined else '--'
  }}</font> |

  {% endif %}

  {% endfor %}
title: Shuttle Schedule

```

## Mushroom Template Card
```yaml
type: custom:mushroom-template-card
primary: Pegasus Express
icon: mdi:bus
secondary: >-
  {% set target_route = "Pegasus Express" %} {% set stops =
  state_attr('sensor.ucf_bus_tracker', 'stops') %} {% if stops %}
    {% set etas = stops[0].etas | selectattr('route', 'eq', target_route) | map(attribute='minutes') | list %}
    {% if etas %}
       Next: {{ etas[0] }} min {% if etas[1] is defined %}& {{ etas[1] }} min{% endif %}
    {% else %}
       No buses scheduled
    {% endif %}
  {% else %}
    Loading...
  {% endif %}
tap_action:
  action: none
color: >-
  {% set target_route = "Pegasus Express" %} {% set stops =
  state_attr('sensor.ucf_bus_tracker', 'stops') %} {% if stops %}
    {% set etas = stops[0].etas | selectattr('route', 'eq', target_route) | map(attribute='minutes') | list %}
    {% if etas and etas[0] <= 5 %} deep-orange {% else %} blue {% endif %}
  {% else %} disabled {% endif %}
features_position: bottom

```
