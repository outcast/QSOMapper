#!/usr/bin/env python3

import adif_io
import sys
import xmltodict
import requests
import traceback
import pandas as pd

# File can be downloaded from https://pota.app/all_parks_ext.csv
CSV_FILE = "all_parks_ext.csv"
def main():
    if len(sys.argv) != 2:
        print("Usage: python pota-mapper.py <adif_file>")
        sys.exit(1)

    adif_file = sys.argv[1]

    parks = pd.read_csv(CSV_FILE)
    my_park = None

    try:
        with open(adif_file, 'r') as f:
            adif_data = f.read()
    except FileNotFoundError:
        print(f"Error: File '{adif_file}' not found.")
        sys.exit(1)

    qsodata, header = adif_io.read_from_file(adif_file)
    map_data = []
    try:
        for qso in qsodata:
            call = qso.get('CALL', 'N/A')
            if call == 'N/A':
                continue
            # Check if cache file exists and read from it if it does
            cache_file = f"/tmp/cache_{call}.xml"
            try:
                with open(cache_file, 'r') as f:
                    call_data = f.read()
                    #print(f"Read cached data for call {call}: {call_data}")
            except FileNotFoundError:
                call_data = requests.get(f"https://www.hamqth.com/dxcc.php?callsign={call}").text
                #print(f"Fetched data for call {call}: {call_data}")
                with open(cache_file, 'w') as f:
                    f.write(call_data)
            call_data = xmltodict.parse(call_data)["HamQTH"]["dxcc"]
            qso["lat"] = call_data["lat"]
            qso["lon"] = call_data["lng"]
            park_lookup = parks[parks['reference'] == qso.get('SIG_INFO')]
            if not park_lookup.empty:
                # CSV has latitude and longitude columns; ensure we assign them correctly
                qso['lat'] = park_lookup['latitude'].values[0]
                qso['lon'] = park_lookup['longitude'].values[0]
            if my_park is None and 'MY_SIG_INFO' in qso:
                my_park = qso['MY_SIG_INFO']
                #print(f"My Park: {my_park}")
            #print(f"Call: {qso.get('CALL')}, Band: {qso.get('BAND')}, Mode: {qso.get('MODE')}, MY_PARK: {qso.get('MY_SIG_INFO')}, P2P: {qso.get('SIG_INFO')}, Lat: {qso['lat']}, Lon: {qso['lon']}")
            map_data.append(qso)
        print(f"Processed QSO with {call}, total QSOs: {len(map_data)}")
    except Exception as e:
        print(f"Error parsing ADIF file:", e)
        # dump stack trace for debugging
        traceback.print_exc()
    print(f"Total QSOs processed: {len(map_data)}")
    if my_park:
        map_data.append({
            'CALL': 'MY_PARK',
            'lat': parks[parks['reference'] == my_park]['latitude'].values[0],
            'lon': parks[parks['reference'] == my_park]['longitude'].values[0],
            'SIG_INFO': my_park
        })
    
    # Write an HTML file with embedded map
    with open("map.html", "w") as f:
        # Use OpenLayers (example provided) instead of Leaflet so the output matches the requested HTML
        f.write("""<html><body>
    <div id=\"mapdiv\" style=\"height:100vh; margin:0; padding:0; touch-action:none; -ms-touch-action:none;\"></div>
    <!-- Workaround: ensure OpenLayers' touch/wheel listeners can call preventDefault by
             forcing passive:false for touchstart/touchmove/wheel when added. This suppresses
             the Chrome intervention warnings about preventDefault inside passive listeners. -->
    <script>
        (function(){
            try {
                var orig = EventTarget.prototype.addEventListener;
                EventTarget.prototype.addEventListener = function(type, listener, options) {
                    var opts = options;
                    if (type === 'touchstart' || type === 'touchmove' || type === 'wheel' || type === 'touchend') {
                        if (typeof options !== 'object' || options === null) {
                            opts = { passive: false };
                        } else if (typeof options === 'object' && options.passive === undefined) {
                            opts = Object.assign({}, options, { passive: false });
                        }
                    }
                    return orig.call(this, type, listener, opts);
                };
            } catch(e) {
                // If monkeypatching fails, silently continue.
            }
        })();
    </script>
    <script src=\"https://www.openlayers.org/api/OpenLayers.js\"></script>
  <script>
    // create map
    map = new OpenLayers.Map("mapdiv");
    map.addLayer(new OpenLayers.Layer.OSM());

    // data array: will be populated from Python
    var data = [""")
        for qso in map_data:
            # Ensure numeric coordinates (cast to float where possible)
            try:
                lat = float(qso.get('lat') or 0)
            except Exception:
                lat = 0
            try:
                lon = float(qso.get('lon') or 0)
            except Exception:
                lon = 0
            # include extra fields for popup details (safely escape quotes)
            call = qso.get('CALL', 'N/A').replace('"', '\\"')
            band = str(qso.get('BAND', '')).replace('"', '\\"')
            mode = str(qso.get('MODE', '')).replace('"', '\\"')
            sig_info = str(qso.get('SIG_INFO', '')).replace('"', '\\"')
            qso_date = str(qso.get('QSO_DATE', '')).replace('"', '\\"')
            qso_time = str(qso.get('TIME_ON', '')).replace('"', '\\"')
            f.write(f"{{CALL: \"{call}\", lat: {lat}, lon: {lon}, BAND: \"{band}\", MODE: \"{mode}\", SIG_INFO: \"{sig_info}\", QSO_DATE: \"{qso_date}\", TIME_ON: \"{qso_time}\"}},")
        f.write(""" ];

    // markers layer
    var markers = new OpenLayers.Layer.Markers( "Markers" );
    map.addLayer(markers);

    // choose a default center (first valid point) and zoom
    var centerLonLat = null;
    var zoom = 3;

        // store popup so only one is shown at a time
        var currentPopup = null;

        data.forEach(function(qso, idx) {
            if ((qso.lon || qso.lon === 0) && (qso.lat || qso.lat === 0)) {
                var lonLat = new OpenLayers.LonLat(qso.lon, qso.lat).transform(
                    new OpenLayers.Projection("EPSG:4326"),
                    map.getProjectionObject()
                );
                                // create marker; use a distinct blue icon for MY_PARK so it's easy to spot
                                var marker;
                                if (qso.CALL === 'MY_PARK') {
                                        var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="30" height="30">'
                                            + '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" fill="#007BFF" stroke="#000" stroke-width="0.5"/>'
                                            + '</svg>';
                                        var iconUrl = 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
                                        var size = new OpenLayers.Size(30,30);
                                        var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
                                        var icon = new OpenLayers.Icon(iconUrl, size, offset);
                                        marker = new OpenLayers.Marker(lonLat, icon);
                                } else {
                                        marker = new OpenLayers.Marker(lonLat);
                                }
                                // attach qso data to marker for event handlers
                                marker.qso = qso;
                // open popup on click/tap to avoid flicker caused by mouseover/mouseout
                marker.events.register('click', marker, function(evt) {
                    try {
                        if (currentPopup) { map.removePopup(currentPopup); currentPopup = null; }
                        var content = '<div style="font-size:12px">'
                            + '<b>' + this.qso.CALL + '</b><br/>'
                            + (this.qso.BAND ? ('Band: ' + this.qso.BAND + '<br/>') : '')
                            + (this.qso.MODE ? ('Mode: ' + this.qso.MODE + '<br/>') : '')
                            + (this.qso.SIG_INFO ? ('P2P: ' + this.qso.SIG_INFO + '<br/>') : '')
                            + (this.qso.QSO_DATE ? ('Date: ' + this.qso.QSO_DATE + '<br/>') : '')
                            + (this.qso.TIME_ON ? ('Time: ' + this.qso.TIME_ON + '<br/>') : '')
                            + '</div>';
                        currentPopup = new OpenLayers.Popup.FramedCloud("qsoPopup_" + idx,
                            lonLat,
                            null,
                            content,
                            null,
                            true
                        );
                        map.addPopup(currentPopup);
                        // prevent map from also handling the click and immediately closing the popup
                        OpenLayers.Event.stop(evt);
                    } catch(e) { /* ignore popup errors */ }
                });

                // close popup when clicking on the map background
                if (!map._qsoPopupCloseRegistered) {
                  map.events.register('click', map, function(evt) {
                    try {
                      if (currentPopup) { map.removePopup(currentPopup); currentPopup = null; }
                    } catch(e) {}
                  });
                  map._qsoPopupCloseRegistered = true;
                }
                markers.addMarker(marker);
                if (centerLonLat === null) {
                    centerLonLat = lonLat;
                }
            }
        });

    if (centerLonLat !== null) {
      map.setCenter(centerLonLat, zoom);
    } else {
      // fallback center
      var fallback = new OpenLayers.LonLat(0,0).transform(new OpenLayers.Projection("EPSG:4326"), map.getProjectionObject());
      map.setCenter(fallback, 1);
    }
  </script>
</body></html>
""")
    print("Map written to map.html")

if __name__ == "__main__":
    main()
