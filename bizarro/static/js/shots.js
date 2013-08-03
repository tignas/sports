function draw_half_court(multiplier, flip) {
    var height = 50;
    var width = 94;
    //Draw Graph
    var shot_chart = d3.select('#shot_chart')
        .append('svg')
        .attr('width', width*multiplier)
        .attr('height', height*multiplier)
    //Court
    var court = shot_chart.append('g')
    if (flip) {
        court.attr('transform', 'rotate(180 ' + width*multiplier/4 + ' ' 
                                              + height*multiplier/2 + ')')
    }
    //paint
    court.append('rect')
         .attr('x', 0*multiplier)
         .attr('y', (height-16)/2*multiplier)
         .attr('height', 16*multiplier)
         .attr('width', (18+10/12)*multiplier)
         .attr('fill', 'None')
         .attr('stroke', 'black')
              
    //free throw circle
    court.append('circle')
         .attr('cx', (18+10/12)*multiplier)
         .attr('cy', height/2*multiplier)
         .attr('r', 6*multiplier)
         .attr('fill', 'None')
         .attr('stroke', 'black')
              
    //half-court
    court.append('line')
         .attr('x1', width/2*multiplier)
         .attr('x2', width/2*multiplier)
         .attr('y1', 0)
         .attr('y2', height*multiplier)
         .attr('stroke', 'black')          
    court.append('circle')
         .attr('cx', width/2*multiplier)
         .attr('cy', height/2*multiplier)
         .attr('r', 6*multiplier)
         .attr('fill', 'None')
         .attr('stroke', 'black')
    court.append('circle')
         .attr('cx', width/2*multiplier)
         .attr('cy', height/2*multiplier)
         .attr('r', 2*multiplier)
         .attr('fill', 'None')
         .attr('stroke', 'black')
    //hoop
    court.append('line')
         .attr('x1', 4*multiplier)
         .attr('x2', 4*multiplier)
         .attr('y1', (height - 6)/2*multiplier)
         .attr('y2', (height + 6)/2*multiplier)
         .attr('stroke', 'black')
    //three-point line
    court.append('line')
         .attr('x1', 0*multiplier)
         .attr('x2', 14*multiplier)
         .attr('y1', 3*multiplier)
         .attr('y2', 3*multiplier)
         .attr('stroke', 'black')
    court.append('line')
         .attr('x1', 0*multiplier)
         .attr('x2', 14*multiplier)
         .attr('y1', (height-3)*multiplier)
         .attr('y2', (height-3)*multiplier)
         .attr('stroke', 'black')
    court.append('path')
         .attr('d', 'M' + 14*multiplier + ', ' + 3*multiplier + ' ' +
                    'A' + 28*multiplier + ', ' + (height/2)*multiplier 
                        + ' 0 0,1 ' 
                        + 28*multiplier + ', ' + height/2*multiplier + ' ' +
                    'A' + 28*multiplier + ', ' + (height/2)*multiplier 
                        + ' 0 0,1 ' 
                        + 14*multiplier + ', ' + (height-3)*multiplier)
         .attr('fill', 'None')
         .attr('stroke', 'black')
    court.append('line')
         .attr('x1', (width)*multiplier)
         .attr('x2', (width-14)*multiplier)
         .attr('y1', 3*multiplier)
         .attr('y2', 3*multiplier)
         .attr('stroke', 'black')
    return court;
};

function draw_full_court(multiplier) {
    var court = draw_half_court(multiplier);
    var second_court = draw_half_court(multiplier, 'flip');
};
    


              
var draw_shots = function(shot_data, multiplier, shot_radius) {
    var shot_chart = d3.select('#shot_chart svg');
    d3.select('#shots').remove();
    var shots = shot_chart.append('g')
    var shot = shots.selectAll('g')
                    .data(shot_data)
                    .enter()
                    .append('g')
    shot.append('circle')
        .attr('cx', function(shot) {
                            return shot.y * multiplier
                        })
        .attr('cy', function(shot){
                            return shot.x * multiplier
                        })
        .attr('r', shot_radius)
        .attr('fill', function(shot){
                            if (shot.make) {
                                return 'blue'
                            }
                            else {
                                return 'red'
                            }
                            
                        })
    shot.append('svg:text')
        .attr('x', function(shot) {
                        return shot.y * multiplier
                    })
        .attr('y', function(shot){
                        return shot.x * multiplier
                    })
};
var draw_frequency_shots = function(shot_data, multiplier) {
    var shot_chart = d3.select('#shot_chart svg');
    var red = d3.rgb('#A63E2A');
    var blue = d3.rgb('#293D66');
    d3.select('#shots').remove();
    var shots = shot_chart.append('g')
    var shot = shots.selectAll('g')
                    .data(shot_data)
                    .enter()
                    .append('g')
    shot.append('circle')
        .attr('cx', function(shot) {
                            return shot.y * multiplier
                        })
        .attr('cy', function(shot){
                            return shot.x * multiplier
                        })
        .attr('r', function(shot) {
                            return shot.shots.length*2
        })
        .attr('fill', function(shot){
                            var make_pct = shot.makes/(shot.misses + shot.makes)
                            var ppp = make_pct * shot.points
                            if (ppp > 1.25) {
                                return blue.darker(ppp);
                            } else if (ppp > 1) {
                                return blue.brighter(ppp);
                            } else if (ppp > 0.7) {
                                return red.brighter(ppp);
                            } else {
                                return red.darker(ppp);
                            }
                        })
};











