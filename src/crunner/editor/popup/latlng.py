from folium.features import LatLngPopup
from jinja2 import Template


class LatLngPrecisionPopup(LatLngPopup):
    _template = Template(
        """
            {% macro script(this, kwargs) %}
                var {{this.get_name()}} = L.popup();
                function latLngPop(e) {
                    {{this.get_name()}}
                        .setLatLng(e.latlng)
                        .setContent("Latitude: " + e.latlng.lat.toFixed(7) +
                                    "<br>Longitude: " + e.latlng.lng.toFixed(7))
                        .openOn({{this._parent.get_name()}});
                    }
                {{this._parent.get_name()}}.on('click', latLngPop);
            {% endmacro %}
        """
    )

    def __init__(self):
        super(LatLngPrecisionPopup, self).__init__()
        self._name = "LatLngPrecisionPopup"
