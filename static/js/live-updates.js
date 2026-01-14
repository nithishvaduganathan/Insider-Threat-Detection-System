 $(document).ready(function() {
    // Variable to store the last update time of the logs
    let lastUpdateTime = null;
    
    // Function to update logs table and related components
    function updateLogsTable() {
        $.ajax({
            url: '/api/live_logs',
            type: 'GET',
            success: function(data) {
                // Check if there's new data by comparing the timestamp of the first log
                if (data.length > 0) {
                    const currentUpdateTime = data[0].timestamp;
                    
                    // If this is the first time, set the lastUpdateTime
                    if (!lastUpdateTime) {
                        lastUpdateTime = currentUpdateTime;
                    }
                    
                    // If the data has been updated, update all components
                    if (currentUpdateTime !== lastUpdateTime) {
                        lastUpdateTime = currentUpdateTime;
                        
                        // Update logs table
                        var tbody = $('#logs-table tbody');
                        tbody.empty();
                        
                        var flaggedCount = 0;
                        var alerts = [];
                        
                        data.forEach(function(log) {
                            var statusClass = log.is_red_team ? 'status-flagged' : 'status-normal';
                            var statusText = log.is_red_team ? 'FLAGGED' : 'NORMAL';
                            
                            var row = $('<tr>');
                            row.append($('<td>').text(log.user_id));
                            row.append($('<td>').text(log.email));
                            row.append($('<td>').text(log.login_duration_hours + ' hrs'));
                            row.append($('<td>').text(log.file_access_count));
                            row.append($('<td>').text(log.usb_plug_count));
                            row.append($('<td>').text(log.email_total_count));
                            row.append($('<td>').text(log.email_suspicious_count));
                            row.append($('<td>').text(log.anomaly_score.toFixed(2)));
                            row.append($('<td>').html('<span class="status-badge ' + statusClass + '">' + statusText + '</span>'));
                            
                            tbody.append(row);
                            
                            if (log.is_red_team) {
                                flaggedCount++;
                                alerts.push({
                                    user: log.user_id,
                                    score: log.anomaly_score,
                                    time: log.timestamp
                                });
                            }
                        });
                        
                        // Update statistics
                        $('#flagged-users').text(flaggedCount);
                        var percentage = (flaggedCount / data.length) * 100;
                        $('#threat-percentage').css('width', percentage + '%');
                        $('#threat-percentage').attr('aria-valuenow', Math.round(percentage));
                        $('#threat-percentage-text').text(percentage.toFixed(1) + '%');
                        
                        // Update last updated time
                        var now = new Date();
                        $('#last-updated').text(now.toLocaleTimeString());
                        
                        // Update alerts
                        updateAlerts(alerts);
                        
                        // Update threat chart
                        updateThreatChart(data);
                        
                        // Update PyVis graph (only when logs are updated)
                        updatePyVisGraph();
                    }
                }
            },
            error: function() {
                console.error('Error fetching logs');
            }
        });
    }
    
    // Function to update alerts
    function updateAlerts(alerts) {
        var alertsContainer = $('#alerts-container');
        alertsContainer.empty();
        
        if (alerts.length === 0) {
            alertsContainer.append('<p class="text-muted text-center">No recent alerts</p>');
        } else {
            alerts.slice(0, 5).forEach(function(alert) {
                var alertItem = $('<div class="alert-item">');
                alertItem.append('<strong>' + alert.user + '</strong> flagged as threat (Score: ' + alert.score.toFixed(2) + ')');
                alertItem.append('<small class="float-right">' + new Date(alert.time).toLocaleTimeString() + '</small>');
                alertsContainer.append(alertItem);
            });
        }
    }
    
    // Function to update threat chart
    function updateThreatChart(data) {
        var ctx = document.getElementById('threat-chart').getContext('2d');
        
        // Count users by threat level
        var lowRisk = 0;
        var mediumRisk = 0;
        var highRisk = 0;
        
        data.forEach(function(log) {
            if (log.anomaly_score < 0.3) {
                lowRisk++;
            } else if (log.anomaly_score < 0.7) {
                mediumRisk++;
            } else {
                highRisk++;
            }
        });
        
        // Update chart
        if (window.threatChart) {
            window.threatChart.data.datasets[0].data = [lowRisk, mediumRisk, highRisk];
            window.threatChart.update();
        } else {
            window.threatChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Low Risk', 'Medium Risk', 'High Risk'],
                    datasets: [{
                        data: [lowRisk, mediumRisk, highRisk],
                        backgroundColor: [
                            'rgba(46, 204, 113, 0.7)',
                            'rgba(241, 196, 15, 0.7)',
                            'rgba(231, 76, 60, 0.7)'
                        ],
                        borderColor: [
                            'rgba(46, 204, 113, 1)',
                            'rgba(241, 196, 15, 1)',
                            'rgba(231, 76, 60, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    legend: {
                        position: 'bottom'
                    }
                }
            });
        }
    }
    
    // Function to update PyVis graph
    function updatePyVisGraph() {
        // Show loading indicator
        $('.graph-container').addClass('loading');
        
        // Call API to regenerate graph
        $.ajax({
            url: '/api/regenerate_graph',
            type: 'GET',
            success: function(response) {
                if (response.success) {
                    // Get the iframe element
                    var iframe = $('.network-graph');
                    
                    // Update the iframe src with a timestamp to prevent caching
                    var timestamp = new Date().getTime();
                    var src = "/static/" + response.graph_path + "?t=" + timestamp;
                    iframe.attr("src", src);

                    
                    // Hide loading indicator when iframe is loaded
                    iframe.on('load', function() {
                        $('.graph-container').removeClass('loading');
                    });
                } else {
                    console.error('Error regenerating graph:', response.error);
                    $('.graph-container').removeClass('loading');
                }
            },
            error: function() {
                console.error('Error calling graph regeneration API');
                $('.graph-container').removeClass('loading');
            }
        });
    }
    
    // Initial update
    updateLogsTable();
    
    // Update every 10 seconds to check for new logs
    setInterval(updateLogsTable, 10000);
    
    // Manual refresh button
    $('#refresh-btn').click(function() {
        $(this).addClass('fa-spin');
        updateLogsTable();
        setTimeout(function() {
            $('#refresh-btn').removeClass('fa-spin');
        }, 1000);
    });
});