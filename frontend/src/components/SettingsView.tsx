import { FormEvent, useEffect, useState } from "react";
import { fetchAppSettings, searchCities, updateAppSettings } from "../api";
import type { CityOption } from "../types";

export function SettingsView() {
  const [weatherCity, setWeatherCity] = useState("");
  const [savedCity, setSavedCity] = useState("");
  const [selectedCity, setSelectedCity] = useState<CityOption | null>(null);
  const [cityOptions, setCityOptions] = useState<CityOption[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchAppSettings()
      .then((settings) => {
        if (!cancelled) {
          setWeatherCity(settings.weather_city);
          setSavedCity(settings.weather_city);
          if (settings.weather_latitude !== null && settings.weather_longitude !== null) {
            setSelectedCity({
              id: settings.weather_city,
              name: settings.weather_city,
              label: settings.weather_city,
              country: "",
              country_code: "",
              admin1: null,
              latitude: settings.weather_latitude,
              longitude: settings.weather_longitude,
            });
          }
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const query = weatherCity.trim();
    if (query.length < 2 || selectedCity?.label === query) {
      setCityOptions([]);
      setIsSearching(false);
      return;
    }

    let cancelled = false;
    setIsSearching(true);
    const timeout = window.setTimeout(() => {
      searchCities(query)
        .then((cities) => {
          if (!cancelled) {
            setCityOptions(cities);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setCityOptions([]);
          }
        })
        .finally(() => {
          if (!cancelled) {
            setIsSearching(false);
          }
        });
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, [weatherCity, selectedCity]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedCity = weatherCity.trim();
    if (!trimmedCity) {
      setError("Weather city is required.");
      return;
    }

    setIsSaving(true);
    setError(null);
    setStatus("Processing weather data");

    updateAppSettings({
      weather_city: trimmedCity,
      weather_latitude: selectedCity?.latitude ?? null,
      weather_longitude: selectedCity?.longitude ?? null,
    })
      .then((settings) => {
        setWeatherCity(settings.weather_city);
        setSavedCity(settings.weather_city);
        setStatus(
          settings.weather_refresh_status === "processed"
            ? "Saved and processed"
            : "Saved",
        );
      })
      .catch((err: Error) => {
        setError(err.message);
      })
      .finally(() => {
        setIsSaving(false);
      });
  }

  const hasChanges = weatherCity.trim() !== savedCity;

  function chooseCity(city: CityOption) {
    setSelectedCity(city);
    setWeatherCity(city.label);
    setCityOptions([]);
    setStatus(null);
  }

  return (
    <>
      <header className="dashboard-header">
        <div>
          <p>Music Listening Intelligence</p>
          <h1>Settings</h1>
        </div>
      </header>

      {error ? <div className="banner">{error}</div> : null}

      <section className={isLoading ? "panel settings-panel loading" : "panel settings-panel"}>
        <div className="panel-heading">
          <h2>Personalization</h2>
          {status ? <span>{status}</span> : null}
        </div>

        <form className="settings-form" onSubmit={handleSubmit}>
          <label className="settings-field">
            <span>Weather City</span>
            <div className="city-combobox">
              <input
                value={weatherCity}
                onChange={(event) => {
                  setWeatherCity(event.target.value);
                  setSelectedCity(null);
                  setStatus(null);
                }}
                placeholder="Search North America"
                maxLength={120}
                disabled={isLoading || isSaving}
                autoComplete="off"
              />
              {isSearching ? <span className="city-search-status">Searching</span> : null}
              {cityOptions.length ? (
                <div className="city-options" role="listbox">
                  {cityOptions.map((city) => (
                    <button
                      type="button"
                      key={city.id}
                      onClick={() => chooseCity(city)}
                      role="option"
                    >
                      <strong>{city.name}</strong>
                      <span>{city.label}</span>
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </label>

          <button
            className="primary-button"
            type="submit"
            disabled={isLoading || isSaving || !hasChanges}
          >
            {isSaving ? "Saving" : "Save"}
          </button>
        </form>
      </section>
    </>
  );
}
