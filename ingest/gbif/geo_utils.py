import geopy.distance


def get_min_max_coordinates(center_point: tuple, radius_km):
    d = geopy.distance.distance(kilometers=radius_km)
    points = []
    for b in [0, 90, 180, 270]:
        points.append(d.destination(point=center_point, bearing=b))
    return points


def get_lat_lon_cells(included_points, cells_per_axis=24):
    lat_max = max([p[0] for p in included_points])
    lat_min = min([p[0] for p in included_points])
    lon_max = max([p[1] for p in included_points])
    lon_min = min([p[1] for p in included_points])
    lat_step = (lat_max - lat_min) / cells_per_axis
    lon_step = (lon_max - lon_min) / cells_per_axis
    lats = []
    lons = []
    for i in range(cells_per_axis + 1):
        lats.append(lat_min + i * lat_step)
        lons.append(lon_min + i * lon_step)
    return lats, lons


def get_grid_coordinates(lats, lons):
    grid_coordinates = []
    for i in range(1, len(lats)):
        for j in range(1, len(lons)):
            lat_range = (lats[i - 1], lats[i])
            lon_range = (lons[j - 1], lons[j])
            grid_coordinates.append(dict(lat=lat_range, lon=lon_range))
    return grid_coordinates
