import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from report_builder import (
    CHARTS_DIR,
    export_report_pdf,
    extract_for_customer,
    generate_report_draft,
    ga4_run_report,
    gsc_search_analytics_query,
    gsc_url_inspection,
    contentful_list_entries,
    get_report_template,
    list_customers,
    list_report_templates,
    semrush_ai_fetch_report,
    semrush_fetch_report,
    webflow_list_items,
    wordpress_list_posts,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
UI_DIR = ROOT_DIR / "ui"
HOST = "127.0.0.1"
PORT = 8000


class APIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def _write_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_pdf(self, pdf_bytes: bytes, filename: str = "customer-report.pdf"):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(pdf_bytes)))
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def _write_file(self, file_path: Path, content_type: str):
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON payload.") from exc

    def _query_params(self):
        parsed = urlparse(self.path)
        return {k: v[0] for k, v in parse_qs(parsed.query).items() if v}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/customers":
            self._write_json({"customers": list_customers()})
            return
        if path == "/api/health":
            self._write_json({"status": "ok"})
            return
        if path == "/api/gsc/search-analytics":
            self._handle_gsc_search_analytics()
            return
        if path == "/api/gsc/url-inspection":
            self._handle_gsc_url_inspection()
            return
        if path == "/api/ga4/run-report":
            self._handle_ga4_run_report()
            return
        if path == "/api/semrush/report":
            self._handle_semrush_report()
            return
        if path == "/api/semrush-ai/report":
            self._handle_semrush_ai_report()
            return
        if path == "/api/wordpress/posts":
            self._handle_wordpress_posts()
            return
        if path == "/api/webflow/items":
            self._handle_webflow_items()
            return
        if path == "/api/contentful/entries":
            self._handle_contentful_entries()
            return
        if path == "/api/report-templates":
            self._write_json({"templates": list_report_templates()})
            return
        if path.startswith("/api/report-templates/"):
            template_id = path.split("/api/report-templates/")[-1].strip("/")
            try:
                self._write_json(get_report_template(template_id))
            except ValueError as exc:
                self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if path.startswith("/outputs/charts/"):
            filename = path.split("/outputs/charts/")[-1]
            chart_path = CHARTS_DIR / filename
            self._write_file(chart_path, "image/png")
            return
        if path == "/assets/peppercontent_logo.jpeg":
            logo_path = ROOT_DIR / "peppercontent_logo.jpeg"
            self._write_file(logo_path, "image/jpeg")
            return
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._read_json_body()
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/extract":
            self._handle_extract(payload)
            return
        if path in ("/api/reports", "/api/reports/generate"):
            self._handle_generate(payload)
            return
        if path == "/api/reports/pdf":
            self._handle_export_pdf(payload)
            return

        self._write_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_gsc_search_analytics(self):
        params = self._query_params()
        customer_id = params.get("customerId", "")
        dimensions = params.get("dimensions")
        if not customer_id:
            self._write_json(
                {"error": "customerId is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            data = gsc_search_analytics_query(customer_id, dimensions=dimensions)
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json(data)

    def _handle_wordpress_posts(self):
        customer_id = self._query_params().get("customerId", "")
        if not customer_id:
            self._write_json(
                {"error": "customerId is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            data = wordpress_list_posts(customer_id)
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json(data)

    def _handle_webflow_items(self):
        customer_id = self._query_params().get("customerId", "")
        if not customer_id:
            self._write_json(
                {"error": "customerId is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            data = webflow_list_items(customer_id)
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json(data)

    def _handle_contentful_entries(self):
        customer_id = self._query_params().get("customerId", "")
        if not customer_id:
            self._write_json(
                {"error": "customerId is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            data = contentful_list_entries(customer_id)
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json(data)

    def _handle_semrush_ai_report(self):
        params = self._query_params()
        customer_id = params.get("customerId", "")
        report_type = params.get("type", "")
        if not customer_id:
            self._write_json(
                {"error": "customerId is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            data = semrush_ai_fetch_report(customer_id, report_type)
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json(data)

    def _handle_semrush_report(self):
        params = self._query_params()
        customer_id = params.get("customerId", "")
        report_type = params.get("type", "")
        domain = params.get("domain")
        phrase = params.get("phrase")
        if not customer_id:
            self._write_json(
                {"error": "customerId is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            data = semrush_fetch_report(
                customer_id,
                report_type,
                domain=domain,
                phrase=phrase,
            )
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json(data)

    def _handle_ga4_run_report(self):
        params = self._query_params()
        customer_id = params.get("customerId", "")
        report_key = params.get("report", "")
        if not customer_id:
            self._write_json(
                {"error": "customerId is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            data = ga4_run_report(customer_id, report_key)
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json(data)

    def _handle_gsc_url_inspection(self):
        params = self._query_params()
        customer_id = params.get("customerId", "")
        inspection_url = params.get("url", "")
        if not customer_id:
            self._write_json(
                {"error": "customerId is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            data = gsc_url_inspection(customer_id, inspection_url)
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json(data)

    def _handle_extract(self, payload):
        customer_id = payload.get("customerId", "")
        if not customer_id:
            self._write_json(
                {"error": "customerId is required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            data = extract_for_customer(customer_id)
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._write_json(data)

    def _handle_generate(self, payload):
        customer_id = payload.get("customerId", "")
        report_type = payload.get("reportType", "")
        instructions = payload.get("instructions", "")
        included_item_ids = payload.get("includedItemIds", [])

        if not customer_id or not report_type:
            self._write_json(
                {"error": "customerId and reportType are required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            draft = generate_report_draft(
                customer_id,
                report_type,
                instructions,
                included_item_ids=included_item_ids or None,
            )
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._write_json(draft)

    def _handle_export_pdf(self, payload):
        report_markdown = payload.get("reportMarkdown", "").strip()
        customer_name = payload.get("customerName", "").strip()
        report_type = payload.get("reportType", "").strip()
        chart_filenames = payload.get("chartFilenames", [])

        if not report_markdown or not customer_name or not report_type:
            self._write_json(
                {"error": "reportMarkdown, customerName, and reportType are required."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            pdf_bytes = export_report_pdf(
                report_markdown=report_markdown,
                customer_name=customer_name,
                report_type=report_type,
                chart_filenames=chart_filenames,
            )
        except Exception as exc:
            self._write_json(
                {"error": f"PDF export failed: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        safe_name = "".join(ch if ch.isalnum() else "_" for ch in customer_name).strip("_")
        filename = f"{safe_name or 'customer'}_report.pdf"
        self._write_pdf(pdf_bytes, filename=filename)


def run_server():
    server = ThreadingHTTPServer((HOST, PORT), APIHandler)
    print(f"Serving Pepper prototype at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
