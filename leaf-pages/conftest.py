import pytest
import time
import os

# Global variables to track session stats
session_start_time = 0
total_errors = 0
matrix_results = {}

def pytest_metadata(metadata):
    """Clear metadata to remove the Environment section from the HTML report."""
    metadata.clear()

def pytest_sessionstart(session):
    global session_start_time
    session_start_time = time.time()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    
    # Attach status code to the report object
    if hasattr(item, "cls") and hasattr(item.cls, "status_code"):
        report.user_status_code = item.cls.status_code

    if report.when == "call":
        # Attach the screenshot path to the report object so it gets serialized and sent to xdist master node
        instance = getattr(item, "instance", None)
        if instance and hasattr(instance, "screenshot_path"):
            report.user_screenshot_path = instance.screenshot_path

def pytest_runtest_logreport(report):
    """This hook runs on the master node and collects results from all workers."""
    global total_errors, matrix_results
    
    # We want to log the outcome if it's a test run ("call") OR if it failed during setup
    if report.when == "call" or (report.when == "setup" and report.failed):
        if report.failed:
            total_errors += 1
            error_msg = getattr(report, "longreprtext", str(report.longrepr) if hasattr(report, "longrepr") else "")
            import html as html_lib
            error_msg_html = html_lib.escape(error_msg).replace('\n', '<br>')
        else:
            error_msg_html = ""
            
        url = report.nodeid.split("[")[-1].split("]")[0]
        test_name = report.nodeid.split("::")[-1].split("[")[0]
        
        if "test_Section_" in test_name:
            section = " ".join(test_name.split("_")[3:])
        else:
            section = test_name
            
        screenshot_path = getattr(report, "user_screenshot_path", "")
            
        if url not in matrix_results:
            matrix_results[url] = {}
            
        if hasattr(report, "user_status_code"):
            matrix_results[url]["Status Code"] = report.user_status_code
            
        matrix_results[url][section] = {
            "status": report.outcome,
            "screenshot": screenshot_path,
            "error_msg": error_msg_html
        }

def pytest_html_report_title(report):
    report.title = "Detailed Dividends UI Test Report"

def pytest_html_results_summary(prefix, summary, postfix, session):
    global session_start_time, total_errors
    total_time = time.time() - session_start_time
    total_test_cases = session.testscollected
    total_suites = 1 
    
    # Prepend custom detailed metrics to the HTML report summary section
    custom_html = f"""
    <div style="margin-bottom: 25px; font-family: sans-serif;">
        <h3 style="margin-bottom: 15px; color: #333; font-size: 18px;">Detailed Execution Metrics</h3>
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 150px; background: #fff; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 5px solid #17a2b8;">
                <div style="font-size: 12px; color: #6c757d; text-transform: uppercase; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">Total Time</div>
                <div style="font-size: 24px; font-weight: 800; color: #212529;">{total_time:.2f}s</div>
            </div>
            <div style="flex: 1; min-width: 150px; background: #fff; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 5px solid #6f42c1;">
                <div style="font-size: 12px; color: #6c757d; text-transform: uppercase; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">Total Suites</div>
                <div style="font-size: 24px; font-weight: 800; color: #212529;">{total_suites}</div>
            </div>
            <div style="flex: 1; min-width: 150px; background: #fff; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 5px solid #007bff;">
                <div style="font-size: 12px; color: #6c757d; text-transform: uppercase; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">Test Cases</div>
                <div style="font-size: 24px; font-weight: 800; color: #212529;">{total_test_cases}</div>
            </div>
            <div style="flex: 1; min-width: 150px; background: #fff; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 5px solid #dc3545;">
                <div style="font-size: 12px; color: #6c757d; text-transform: uppercase; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">Errors / Failures</div>
                <div style="font-size: 24px; font-weight: 800; color: #212529;">{total_errors}</div>
            </div>
        </div>
        <div style="margin-top: 20px; text-align: center;">
            <a href="matrix_report.html" style="display: inline-block; padding: 12px 24px; font-size: 16px; font-weight: bold; color: #fff; background-color: #007bff; border-radius: 5px; text-decoration: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">Open Matrix Report</a>
        </div>
    </div>
    """
    prefix.extend([custom_html])

def pytest_sessionfinish(session, exitstatus):
    # Only generate the report on the master node, to prevent workers from overwriting it with empty data
    if hasattr(session.config, "workerinput"):
        return
        
    # Generate the custom matrix HTML
    sections = [
        "Header and Meta", "Analytics Tags", "Graph and Chart", 
        "Content Tabs", "Live Stats and Market Cap", "Dividend Metrics", 
        "History Table", "FAQs", "Footer Components"
    ]
    
    section_display = {
        "Header and Meta": "Header",
        "Analytics Tags": "Analytics",
        "Graph and Chart": "Graph",
        "Content Tabs": "Overview",
        "Live Stats and Market Cap": "Live Stats",
        "Dividend Metrics": "Dividend Metrics",
        "History Table": "Corporate Actions",
        "FAQs": "FAQ",
        "Footer Components": "Quick Links"
    }
    
    html = ["<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>Allure-Style Matrix Report</title>"]
    html.append('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">')
    html.append('<link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">')
    html.append('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">')
    
    html.append('<style>')
    html.append('body { background-color: #f4f6f8; font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #333; }')
    html.append('.status-pass { color: #97cc64; font-size: 1.2rem; }')
    html.append('.status-fail { color: #fd5a3e; font-size: 1.2rem; cursor: pointer; }')
    html.append('.status-skip { color: #ffd050; font-size: 1.2rem; }')
    html.append('.url-col { max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }')
    html.append('.card { border: none; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); margin-bottom: 20px; }')
    html.append('.nav-pills .nav-link.active, .nav-pills .show>.nav-link { background-color: #3b4151; color: white; }')
    html.append('.nav-link { color: #3b4151; font-weight: 500; }')
    html.append('.metric-value { font-size: 2.5rem; font-weight: 700; line-height: 1; }')
    html.append('.metric-label { font-size: 0.85rem; text-transform: uppercase; color: #6c757d; font-weight: 600; letter-spacing: 0.5px; }')
    html.append('</style></head><body>')
    
    html.append('<div class="d-flex" style="height: 100vh; overflow: hidden;">')
    # Sidebar
    html.append('<div class="bg-white border-end d-flex flex-column" style="width: 250px;">')
    html.append('<div class="p-4 border-bottom"><h4 class="m-0 fw-bold" style="color: #3b4151;"><i class="fa-solid fa-layer-group me-2"></i>Report</h4></div>')
    html.append('<div class="p-3">')
    html.append('<ul class="nav nav-pills flex-column" id="myTab" role="tablist">')
    html.append('<li class="nav-item" role="presentation"><button class="nav-link active w-100 text-start" id="overview-tab" data-bs-toggle="tab" data-bs-target="#overview" type="button" role="tab"><i class="fa-solid fa-chart-pie me-2"></i>Overview</button></li>')
    html.append('<li class="nav-item mt-2" role="presentation"><button class="nav-link w-100 text-start" id="suites-tab" data-bs-toggle="tab" data-bs-target="#suites" type="button" role="tab"><i class="fa-solid fa-table-list me-2"></i>Suites / Matrix</button></li>')
    html.append('</ul>')
    html.append('</div></div>')
    
    # Main Content Area
    html.append('<div class="flex-grow-1 p-4" style="overflow-y: auto;">')
    html.append('<div class="tab-content" id="myTabContent">')
    
    # Process Metrics
    total_urls = len(matrix_results)
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skipped_tests = 0
    
    for data in matrix_results.values():
        for sec in sections:
            res = data.get(sec)
            if res:
                total_tests += 1
                if res["status"] == "passed": passed_tests += 1
                elif res["status"] == "failed": failed_tests += 1
                else: skipped_tests += 1
    
    pass_pct = (passed_tests / total_tests * 100) if total_tests else 0
    
    # --- OVERVIEW TAB ---
    html.append('<div class="tab-pane fade show active" id="overview" role="tabpanel" tabindex="0">')
    html.append('<h2 class="mb-4 text-secondary">Overview</h2>')
    html.append('<div class="row">')
    
    # Environment & Metrics Card
    html.append('<div class="col-md-7">')
    html.append('<div class="card h-100"><div class="card-body p-4">')
    html.append('<h5 class="card-title border-bottom pb-2 mb-4">Environment Metrics</h5>')
    html.append('<div class="row text-center mb-4">')
    html.append(f'<div class="col-4"><div class="metric-value" style="color: #3b4151;">{total_tests}</div><div class="metric-label mt-2">Total Checks</div></div>')
    html.append(f'<div class="col-4"><div class="metric-value" style="color: #97cc64;">{passed_tests}</div><div class="metric-label mt-2">Passed</div></div>')
    html.append(f'<div class="col-4"><div class="metric-value" style="color: #fd5a3e;">{failed_tests}</div><div class="metric-label mt-2">Failed</div></div>')
    html.append('</div>')
    html.append('<div class="row text-center">')
    html.append(f'<div class="col-4"><div class="metric-value" style="color: #ffd050;">{skipped_tests}</div><div class="metric-label mt-2">Skipped</div></div>')
    html.append(f'<div class="col-4"><div class="metric-value" style="color: #007bff;">{total_urls}</div><div class="metric-label mt-2">URLs Processed</div></div>')
    html.append(f'<div class="col-4"><div class="metric-value text-secondary">{pass_pct:.1f}%</div><div class="metric-label mt-2">Pass Rate</div></div>')
    html.append('</div>')
    html.append('</div></div></div>')
    
    # Chart Card
    html.append('<div class="col-md-5">')
    html.append('<div class="card h-100"><div class="card-body p-4 d-flex flex-column align-items-center justify-content-center">')
    html.append('<h5 class="card-title w-100 border-bottom pb-2 mb-4">Results Distribution</h5>')
    html.append('<div style="width: 250px; height: 250px;"><canvas id="resultChart"></canvas></div>')
    html.append('</div></div></div>')
    
    html.append('</div>') # end row
    
    # --- TABLE SECTION IN OVERVIEW ---
    html.append('<h3 class="mt-5 mb-4 text-secondary">Test Execution Matrix</h3>')
    html.append('<div class="card"><div class="card-body">')
    html.append('<div class="table-responsive">')
    html.append('<table id="matrixTable" class="table table-hover align-middle text-center" style="width:100%">')
    html.append('<thead class="table-light"><tr><th class="text-start">URL</th><th>Status Code</th>')
    for sec in sections:
        html.append(f"<th>{section_display.get(sec, sec)}</th>")
    html.append('</tr></thead><tbody>')

    modal_html = []
    modal_idx = 0

    for url, data in matrix_results.items():
        status_code = data.get("Status Code", "-")
        status_badge = "success" if str(status_code) == "200" else "danger"
        html.append(f"<tr><td class='text-start url-col'><a href='{url}' target='_blank' class='text-decoration-none' title='{url}'>{url}</a></td>")
        html.append(f"<td><span class='badge bg-{status_badge}'>{status_code}</span></td>")
        for sec in sections:
            result = data.get(sec)
            if not result:
                html.append("<td class='text-muted'>-</td>")
            else:
                status = result["status"]
                err = result.get("error_msg", "")
                scr = result.get("screenshot", "")
                
                if status == "passed":
                    icon = '<i class="fa-solid fa-circle-check status-pass"></i>'
                    if scr and os.path.exists(scr):
                        html.append(f"<td><a href='{scr}' target='_blank' title='View Screenshot'>{icon}</a></td>")
                    else:
                        html.append(f"<td>{icon}</td>")
                elif status == "failed":
                    icon = '<i class="fa-solid fa-circle-xmark status-fail"></i>'
                    modal_idx += 1
                    modal_id = f"errorModal{modal_idx}"
                    html.append(f"<td><a href='#' data-bs-toggle='modal' data-bs-target='#{modal_id}' title='View Error Details'>{icon}</a></td>")
                    
                    scr_link = f"<div class='mt-3'><a href='{scr}' target='_blank' class='btn btn-sm btn-outline-danger'><i class='fa-solid fa-image me-1'></i> View Screenshot</a></div>" if scr and os.path.exists(scr) else ""
                    
                    modal_html.append(f"""
                    <div class="modal fade text-start" id="{modal_id}" tabindex="-1" aria-hidden="true">
                      <div class="modal-dialog modal-lg modal-dialog-centered">
                        <div class="modal-content">
                          <div class="modal-header text-white" style="background-color: #fd5a3e;">
                            <h5 class="modal-title"><i class="fa-solid fa-triangle-exclamation me-2"></i>Test Failure: {section_display.get(sec, sec)}</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                          </div>
                          <div class="modal-body">
                            <h6 class="text-secondary mb-3 text-break">{url}</h6>
                            <div class="p-3 bg-light border rounded font-monospace" style="font-size:13px; max-height:400px; overflow-y:auto; color: #d63384;">
                                {err}
                            </div>
                            {scr_link}
                          </div>
                        </div>
                      </div>
                    </div>
                    """)
                else:
                    html.append('<td><i class="fa-solid fa-circle-exclamation status-skip"></i></td>')
                    
        html.append("</tr>")
        
    html.append("</tbody></table></div></div></div>")
    html.extend(modal_html)
    
    html.append('</div>') # end overview tab
    
    # --- SUITES / MATRIX TAB ---
    html.append('<div class="tab-pane fade" id="suites" role="tabpanel" tabindex="0">')
    html.append('<div class="alert alert-info"><i class="fa-solid fa-info-circle me-2"></i>The matrix table is now available on the Overview dashboard.</div>')
    html.append('</div>') # end suites tab
    
    html.append('</div>') # end tab content
    html.append('</div>') # end main content
    html.append('</div>') # end app flex container
    
    # Scripts
    html.append('<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>')
    html.append('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>')
    html.append('<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>')
    html.append('<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>')
    html.append('<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>')
    
    html.append('<script>')
    html.append('$(document).ready(function() {')
    html.append('  $("#matrixTable").DataTable({')
    html.append('    "pageLength": 50,')
    html.append('    "order": []')
    html.append('  });')
    
    # Chart.js Logic
    html.append('  const ctx = document.getElementById("resultChart").getContext("2d");')
    html.append('  new Chart(ctx, {')
    html.append('    type: "doughnut",')
    html.append('    data: {')
    html.append('      labels: ["Passed", "Failed", "Skipped"],')
    html.append('      datasets: [{')
    html.append(f'        data: [{passed_tests}, {failed_tests}, {skipped_tests}],')
    html.append('        backgroundColor: ["#97cc64", "#fd5a3e", "#ffd050"],')
    html.append('        borderWidth: 0')
    html.append('      }]')
    html.append('    },')
    html.append('    options: { cutout: "70%", plugins: { legend: { position: "bottom" } } }')
    html.append('  });')
    
    html.append('});')
    html.append('</script>')
    html.append('</body></html>')
    
    # We must use absolute path or make sure we write in the correct directory.
    # We will write to current working directory where tests were run.
    with open("matrix_report.html", "w", encoding="utf-8") as f:
        f.write("".join(html))
