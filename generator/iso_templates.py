"""Small ISO 20022 style XML builders for synthetic bank messages (Task 4).

The XML is simplified: it keeps the real message namespaces and the fields Task 7 reads
(UETR, end-to-end id, amount, currency, debtor, creditor, status) and nothing else.
Everything is synthetic.
"""

from xml.sax.saxutils import escape

NS_PACS008 = "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"
NS_PACS002 = "urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10"
NS_CAMT053 = "urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"


def _amount(value: float) -> str:
    return f"{value:.2f}"


def pacs008(
    msg_id: str, uetr: str, end_to_end_id: str, amount: float, currency: str,
    debtor: str, creditor: str, ts: str,
) -> str:
    """Customer credit transfer: the payment instruction."""
    return (
        f'<Document xmlns="{NS_PACS008}"><FIToFICstmrCdtTrf>'
        f"<GrpHdr><MsgId>{escape(msg_id)}</MsgId><CreDtTm>{ts}</CreDtTm></GrpHdr>"
        "<CdtTrfTxInf>"
        f"<PmtId><EndToEndId>{escape(end_to_end_id)}</EndToEndId><UETR>{uetr}</UETR></PmtId>"
        f'<IntrBkSttlmAmt Ccy="{currency}">{_amount(amount)}</IntrBkSttlmAmt>'
        f"<Dbtr><Nm>{escape(debtor)}</Nm></Dbtr>"
        f"<Cdtr><Nm>{escape(creditor)}</Nm></Cdtr>"
        "</CdtTrfTxInf></FIToFICstmrCdtTrf></Document>"
    )


def pacs002(
    msg_id: str, uetr: str, end_to_end_id: str, amount: float, currency: str,
    status: str, ts: str,
) -> str:
    """Payment status report: ACSC means settlement completed."""
    return (
        f'<Document xmlns="{NS_PACS002}"><FIToFIPmtStsRpt>'
        f"<GrpHdr><MsgId>{escape(msg_id)}</MsgId><CreDtTm>{ts}</CreDtTm></GrpHdr>"
        "<TxInfAndSts>"
        f"<OrgnlEndToEndId>{escape(end_to_end_id)}</OrgnlEndToEndId>"
        f"<OrgnlUETR>{uetr}</OrgnlUETR>"
        f"<TxSts>{escape(status)}</TxSts>"
        f'<OrgnlTxRef><IntrBkSttlmAmt Ccy="{currency}">{_amount(amount)}'
        "</IntrBkSttlmAmt></OrgnlTxRef>"
        "</TxInfAndSts></FIToFIPmtStsRpt></Document>"
    )


def camt053(
    msg_id: str, uetr: str, end_to_end_id: str, amount: float, currency: str,
    creditor: str, ts: str,
) -> str:
    """Account statement with one booked credit entry."""
    return (
        f'<Document xmlns="{NS_CAMT053}"><BkToCstmrStmt>'
        f"<GrpHdr><MsgId>{escape(msg_id)}</MsgId><CreDtTm>{ts}</CreDtTm></GrpHdr>"
        "<Stmt><Ntry>"
        f'<Amt Ccy="{currency}">{_amount(amount)}</Amt>'
        "<CdtDbtInd>CRDT</CdtDbtInd><Sts>BOOK</Sts>"
        "<NtryDtls><TxDtls><Refs>"
        f"<EndToEndId>{escape(end_to_end_id)}</EndToEndId><UETR>{uetr}</UETR>"
        f"</Refs><RltdPties><Cdtr><Nm>{escape(creditor)}</Nm></Cdtr></RltdPties>"
        "</TxDtls></NtryDtls></Ntry></Stmt></BkToCstmrStmt></Document>"
    )