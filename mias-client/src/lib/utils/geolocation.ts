/**
 * Shared geolocation helper.
 * Prompts the browser for the user's current position and returns it.
 * Throws a descriptive Error if geolocation is unavailable or denied.
 */

export interface GeoPosition {
  lat: number;
  lng: number;
  accuracy: number;
}

export async function getCurrentPosition(): Promise<GeoPosition> {
  if (!navigator.geolocation) {
    throw new Error('Geolocation is not supported by your browser.');
  }

  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
      },
      (err) => {
        switch (err.code) {
          case err.PERMISSION_DENIED:
            reject(new Error('Location permission denied. Please allow location access to check in.'));
            break;
          case err.POSITION_UNAVAILABLE:
            reject(new Error('Location information is unavailable. Please try again.'));
            break;
          case err.TIMEOUT:
            reject(new Error('Location request timed out. Please try again.'));
            break;
          default:
            reject(new Error('Unable to determine your location.'));
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    );
  });
}
