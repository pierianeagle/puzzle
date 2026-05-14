"""Register all deployments and serve them in one process."""

from prefect import serve
from prefect.events.schemas.deployment_triggers import DeploymentEventTrigger
from prefect.schedules import Cron

from jfri import RESOURCE_ID
from jfri.flows.alpha_vantage.clean_options_chain import (
    backfill_clean_historic_options_chain as av_backfill_clean_historic_options_chain,
)
from jfri.flows.alpha_vantage.clean_options_chain import (
    clean_historic_options_chain as av_clean_historic_options_chain,
)
from jfri.flows.alpha_vantage.ingest_options_chain import (
    INGESTED_EVENT as ALPHA_VANTAGE_INGESTED_EVENT,
)
from jfri.flows.alpha_vantage.ingest_options_chain import (
    backfill_ingest_historic_options_chain as av_backfill_ingest_historic_options_chain,
)
from jfri.flows.alpha_vantage.ingest_options_chain import (
    ingest_historic_options_chain as av_ingest_historic_options_chain,
)
from jfri.flows.cboe.clean_options_chain import (
    clean_todays_options_chain_flow as cboe_clean_todays_options_chain,
)
from jfri.flows.cboe.ingest_options_chain import (
    INGESTED_EVENT as CBOE_INGESTED_EVENT,
)
from jfri.flows.cboe.ingest_options_chain import (
    ingest_todays_options_chain as cboe_ingest_todays_options_chain,
)

if __name__ == "__main__":
    serve(
        av_ingest_historic_options_chain.to_deployment(
            name="ingest_todays_spx_historic_options_chain_from_av",
            schedule=Cron("30 16 * * 1-5", timezone="America/New_York"),
            parameters={"symbol": "SPX"},
        ),
        av_backfill_ingest_historic_options_chain.to_deployment(
            name="ingest_all_historic_options_chains_from_av",
        ),
        av_clean_historic_options_chain.to_deployment(
            name="clean_todays_spx_historic_options_chain_on_ingest_from_av",
            triggers=[
                DeploymentEventTrigger(
                    enabled=True,
                    expect={ALPHA_VANTAGE_INGESTED_EVENT},
                    match={"prefect.resource.id": RESOURCE_ID},
                    parameters={
                        "symbol": "{{ event.payload.symbol }}",
                        "date": "{{ event.payload.date }}",
                    },
                ),
            ],
        ),
        av_backfill_clean_historic_options_chain.to_deployment(
            name="clean_all_historic_options_chains_from_av",
        ),
        cboe_ingest_todays_options_chain.to_deployment(
            name="ingest_todays_spx_historic_options_chain_from_cboe",
            schedules=[
                # 9:30, 9:45
                Cron("30,45 9 * * 1-5", timezone="America/New_York"),
                # 10:00, 10:15, 10:30, ..., 15:45
                Cron("*/15 10-15 * * 1-5", timezone="America/New_York"),
                # 16:00, 16:15, 16:30
                Cron("0,15,30 16 * * 1-5", timezone="America/New_York"),
            ],
            parameters={"ticker": "SPX"},
        ),
        cboe_clean_todays_options_chain.to_deployment(
            name="clean_todays_spx_historic_options_chain_on_ingest_from_cboe",
            triggers=[
                DeploymentEventTrigger(
                    enabled=True,
                    expect={CBOE_INGESTED_EVENT},
                    match={"prefect.resource.id": RESOURCE_ID},
                    parameters={
                        "ticker": "{{ event.payload.ticker }}",
                        "symbol": "{{ event.payload.symbol }}",
                        "date": "{{ event.payload.date }}",
                    },
                ),
            ],
        ),
    )
