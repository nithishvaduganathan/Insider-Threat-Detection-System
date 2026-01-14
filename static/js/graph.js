 $(document).ready(function() {
    // Set up dimensions
    var container = document.getElementById('graph-container');
    var width = container.offsetWidth;
    var height = 500;
    
    // Create SVG
    var svg = d3.select("#graph-container")
        .append("svg")
        .attr("width", width)
        .attr("height", height);
    
    // Create force simulation
    var simulation = d3.forceSimulation()
        .force("link", d3.forceLink().id(function(d) { return d.id; }).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(function(d) {
            return d.type === 'user' ? 25 : 20;
        }));
    
    // Create tooltip
    var tooltip = d3.select(".tooltip");
    
    // Function to update graph
    function updateGraph() {
        d3.json('/api/graph_data').then(function(graph) {
            // Update links
            var link = svg.selectAll(".link")
                .data(graph.links);
            
            link.enter().append("line")
                .attr("class", "link")
                .merge(link);
            
            link.exit().remove();
            
            // Update nodes
            var node = svg.selectAll(".node")
                .data(graph.nodes);
            
            var nodeEnter = node.enter().append("g")
                .attr("class", function(d) { return "node " + d.type; })
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            
            nodeEnter.append("circle")
                .attr("r", function(d) {
                    if (d.type === 'user') return 15;
                    else return 10;
                })
                .on("mouseover", function(d) {
                    tooltip.transition()
                        .duration(200)
                        .style("opacity", .9);
                    
                    var tooltipText = "";
                    if (d.type === 'user') {
                        tooltipText = d.name + " (" + d.email + ")<br>Anomaly Score: " + d.anomaly_score;
                    } else {
                        tooltipText = d.name;
                    }
                    
                    tooltip.html(tooltipText)
                        .style("left", (d3.event.pageX + 10) + "px")
                        .style("top", (d3.event.pageY - 28) + "px");
                })
                .on("mouseout", function(d) {
                    tooltip.transition()
                        .duration(500)
                        .style("opacity", 0);
                });
            
            nodeEnter.append("text")
                .attr("dy", ".35em")
                .attr("text-anchor", "middle")
                .text(function(d) {
                    if (d.type === 'user') return d.name;
                    return d.name.substring(0, 5) + "...";
                });
            
            node = nodeEnter.merge(node);
            
            node.exit().remove();
            
            // Update simulation
            simulation.nodes(graph.nodes);
            simulation.force("link").links(graph.links);
            simulation.alpha(1).restart();
            
            simulation.on("tick", function() {
                link
                    .attr("x1", function(d) { return d.source.x; })
                    .attr("y1", function(d) { return d.source.y; })
                    .attr("x2", function(d) { return d.target.x; })
                    .attr("y2", function(d) { return d.target.y; });
                
                node
                    .attr("transform", function(d) {
                        return "translate(" + d.x + "," + d.y + ")";
                    });
            });
        }).catch(function(error) {
            console.error('Error loading graph data:', error);
        });
    }
    
    // Drag functions
    function dragstarted(d) {
        if (!d3.event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(d) {
        d.fx = d3.event.x;
        d.fy = d3.event.y;
    }
    
    function dragended(d) {
        if (!d3.event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    
    // Initial update
    updateGraph();
    
    // Update every 30 seconds
    setInterval(updateGraph, 30000);
    
    // Responsive resize
    window.addEventListener('resize', function() {
        width = container.offsetWidth;
        svg.attr("width", width);
        simulation.force("center", d3.forceCenter(width / 2, height / 2));
    });
});