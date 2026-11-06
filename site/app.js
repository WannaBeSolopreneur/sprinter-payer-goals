(function () {
  var data = window.SITE_DATA;
  if (!data) return;

  var company = data.company;
  var profile = data.profile;

  text("brand", company.product);
  text("role", company.role);
  text("by", company.builtBy);
  text("hero-line", company.hero);
  text("disclaimer", company.disclaimer);
  text("scope", data.payer.name + ". " + data.payer.note);
  text("problem-title", company.problemTitle);
  text("problem", company.problem);
  text("solution-title", company.solutionTitle);
  text("solution", company.solution);
  text("asof", data.calendar.line);
  text("footer-line", company.footer);

  var primary = data.goals.filter(function (goal) { return goal.tileRole === "primary"; })[0];
  var support = data.goals.filter(function (goal) { return goal.tileRole !== "primary"; });
  renderPrimary(primary, company.chartCaption);
  renderSupport(support);
  renderActions(data.actions);
  renderHow(data);
  renderAbout(profile);
  drawCharts(primary, support);

  function text(id, value) {
    var node = document.getElementById(id);
    if (node) node.textContent = value || "";
  }

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"]/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch];
    });
  }

  function bar(goal) {
    var width = Math.max(0, Math.min(100, goal.progressRatio * 100));
    var tick = "";
    if (goal.paceRatio != null) {
      var left = Math.max(0, Math.min(100, goal.paceRatio * 100));
      tick = '<i class="pace-tick" style="left:' + left + '%"></i>';
    }
    return '<div class="bar" aria-hidden="true"><span style="width:' + width + '%"></span>' + tick + "</div>";
  }

  function renderPrimary(goal, caption) {
    var root = document.getElementById("primary");
    root.innerHTML =
      '<article class="hero ' + esc(goal.status) + '">' +
        '<div>' +
          '<div class="goal-top"><h2>' + esc(goal.label) + '</h2><span class="pill">' + esc(goal.statusLabel) + "</span></div>" +
          '<p class="hero-target">' + esc(goal.subtitle) + "</p>" +
          '<p class="hero-value">' + esc(goal.currentLabel) + "</p>" +
          '<p class="hero-target">Quarter goal ' + esc(goal.targetLabel) + "</p>" +
          '<p class="pace-share">' + esc(goal.paceShareLabel) + "</p>" +
          '<p class="hero-target">' + esc(goal.quarterShareLabel) + "</p>" +
          bar(goal) +
          '<p class="delta">' + esc(goal.deltaLabel) + "</p>" +
        "</div>" +
        '<div class="chart-wrap"><canvas id="pace-chart"></canvas></div>' +
        '<p class="chart-caption">' + esc(caption) + "</p>" +
      "</article>";
  }

  function renderSupport(goals) {
    var root = document.getElementById("support");
    root.innerHTML = goals.map(function (goal, index) {
      return (
        '<article class="goal ' + esc(goal.status) + '">' +
          '<div class="goal-top"><h3>' + esc(goal.label) + '</h3><span class="pill">' + esc(goal.statusLabel) + "</span></div>" +
          '<p class="goal-target">' + esc(goal.subtitle) + "</p>" +
          '<p class="goal-value">' + esc(goal.currentLabel) + "</p>" +
          '<p class="goal-target">Target ' + esc(goal.targetLabel) + "</p>" +
          bar(goal) +
          '<p class="delta">' + esc(goal.deltaLabel) + "</p>" +
          '<div class="spark"><canvas id="spark-' + index + '"></canvas></div>' +
          '<p class="spark-caption">' + esc(goal.sparkCaption) + "</p>" +
        "</article>"
      );
    }).join("");
  }

  function renderActions(actions) {
    var root = document.getElementById("actions");
    root.innerHTML = "";
    actions.forEach(function (action) {
      var item = document.createElement("li");
      var title = document.createElement("strong");
      title.textContent = action.title;
      item.appendChild(title);
      item.appendChild(document.createTextNode(action.sentence));
      root.appendChild(item);
    });
  }

  function renderHow(page) {
    var build = page.build;
    var root = document.getElementById("how-body");
    var layers = ["staging", "intermediate", "spine", "marts"].map(function (name) {
      var items = (build.layers[name] || []).map(function (model) {
        return "<li><code>" + esc(model.name) + "</code><span>" + esc(model.description) + "</span></li>";
      }).join("");
      var title = name.charAt(0).toUpperCase() + name.slice(1);
      return "<div><h3>" + title + "</h3><ul>" + items + "</ul></div>";
    }).join("");
    var metrics = build.metrics.map(function (metric) {
      return (
        '<article class="metric"><code>' + esc(metric.name) + "</code>" +
        "<p>" + esc(metric.label) + ". " + esc(metric.description) + "</p></article>"
      );
    }).join("");
    root.innerHTML =
      '<img src="architecture.png" alt="Steps from the generator to the payer page">' +
      "<p>" + esc(page.warehouseSentence) + "</p>" +
      '<div class="counts">' +
        "<article class=\"count\"><b>" + esc(build.checks) + "</b><span>checks passed</span></article>" +
        "<article class=\"count\"><b>" + esc(build.dataTests) + "</b><span>data tests</span></article>" +
        "<article class=\"count\"><b>" + esc(build.modelCount) + "</b><span>dbt models</span></article>" +
      "</div>" +
      "<p class=\"quiet\">" + esc(page.calendar.statusRule) + "</p>" +
      "<p>In Snowflake the same filter is a row access policy on payer id. The example SQL is in the analyses folder. This demo applies the filter in the marts and again when it writes the page file.</p>" +
      '<div class="layers">' + layers + "</div>" +
      '<div class="metrics"><h3>Metric definitions</h3>' + metrics + "</div>";
  }

  function renderAbout(person) {
    var root = document.getElementById("about");
    var facts = person.highlights.map(function (line) {
      return "<li>" + esc(line) + "</li>";
    }).join("");
    var school = person.education.map(function (line) {
      return "<li>" + esc(line) + "</li>";
    }).join("");
    var links = person.links.map(function (link) {
      return '<a href="' + esc(link.href) + '">' + esc(link.label) + "</a>";
    }).join("");
    root.innerHTML =
      "<h2>" + esc(person.name) + "</h2>" +
      '<p class="role-line">' + esc(person.title) + " at " + esc(person.employer) + ". " + esc(person.location) + ".</p>" +
      "<ul>" + facts + "</ul>" +
      "<ul>" + school + "</ul>" +
      "<p>" + esc(person.relocate) + "</p>" +
      "<p>" + esc(person.demoNote) + "</p>" +
      '<p class="links">' + links + "</p>";
  }

  function drawCharts(goal, goals) {
    if (typeof Chart === "undefined") return;
    var navy = "#1B2A41";
    var powder = "rgba(167, 199, 231, 0.55)";
    Chart.defaults.font.family = '"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif';
    Chart.defaults.color = navy;
    Chart.defaults.animation = false;
    Chart.defaults.plugins.legend.labels.boxWidth = 12;

    new Chart(document.getElementById("pace-chart"), {
      type: "line",
      data: {
        labels: data.pace.map(function (point) { return point.label; }),
        datasets: [
          {
            label: "Straight-line pace",
            data: data.pace.map(function (point) { return point.pace; }),
            borderColor: navy,
            borderDash: [7, 6],
            borderWidth: 2,
            pointRadius: 0,
            tension: 0,
            fill: false
          },
          {
            label: "Completed visits",
            data: data.pace.map(function (point) { return point.actual; }),
            borderColor: navy,
            backgroundColor: powder,
            borderWidth: 2.5,
            pointRadius: 0,
            tension: 0,
            fill: true,
            spanGaps: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, ticks: { maxTicksLimit: 5 } },
          x: { ticks: { maxTicksLimit: 6 } }
        }
      }
    });

    goals.forEach(function (item, index) {
      var canvas = document.getElementById("spark-" + index);
      if (!canvas || !item.sparkline.length) return;
      new Chart(canvas, {
        type: "line",
        data: {
          labels: item.sparkline.map(function (point) { return point.label; }),
          datasets: [{
            data: item.sparkline.map(function (point) { return point.value; }),
            borderColor: navy,
            backgroundColor: powder,
            borderWidth: 2,
            pointRadius: 0,
            tension: 0,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { display: false },
            y: { display: false }
          }
        }
      });
    });
  }
})();
