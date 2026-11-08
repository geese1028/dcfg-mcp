"""End-to-end smoke test: launch the server over stdio and call each tool."""
import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    params = StdioServerParameters(command="uv", args=["run", "dcfg-mcp"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])
            calls = [
                ("liquid_loop_hydraulics", {"heat_kw": 120, "delta_t_k": 10, "pipe_inner_diameter_mm": 32,
                                            "pipe_length_m": 10, "sum_local_loss_coefficients": 6,
                                            "coupling_cv": [12.5, 12.5]}),
                ("classify_procedure", {"task_description": "Put UPS-A into maintenance bypass",
                                        "service_or_person_in_danger_now": False,
                                        "changes_redundancy_or_topology": True,
                                        "repeatable_routine_task": False}),
                ("classify_corrosion_coupon", {"copper_film_angstrom": 130, "exposure_days": 26,
                                               "silver_film_angstrom": 1300}),
            ]
            for name, args in calls:
                res = await s.call_tool(name, args)
                data = json.loads(res.content[0].text)
                print(f"\n== {name} ==")
                for k in ("flow", "velocity", "pressure_drop_kpa", "classification", "verdict",
                          "missing_items", "copper", "silver", "room_class", "flags"):
                    if k in data:
                        print(f"{k}: {data[k]}")


asyncio.run(main())
