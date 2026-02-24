import httpx
import asyncio

moscow     = (55.7558, 37.6173)
saintp     = (59.9311, 30.3609)

async def get_weather() -> dict:

    async with httpx.AsyncClient() as client:
        msc = client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": moscow[0],
                "longitude": moscow[1],
                "current": "temperature_2m",
                "timezone": "auto",
            },
        )

        spb = client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": saintp[0],
                "longitude": saintp[1],
                "current": "temperature_2m",
                "timezone": "auto",
            },      
        )

        msc_temp, spb_temp = await asyncio.gather(msc, spb)

        msc_temp.raise_for_status()
        spb_temp.raise_for_status()
        msc_temp = msc_temp.json()["current"]["temperature_2m"]
        spb_temp = spb_temp.json()["current"]["temperature_2m"]

        res = {"Температура в Москве": msc_temp, "Температура В Санкт-Петербурге": spb_temp}

    return res

async def get_currencies() -> dict:
    
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://open.er-api.com/v6/latest/RUB"
        )

        res.raise_for_status()
        res = res.json()
        res = res.get("rates")
    
    return {
        "USD": f"{(1 / res['USD']):.2f} RUB",
        "EUR": f"{(1 / res['EUR']):.2f} RUB",
    }
