function draw_court(multiplier, shot_radius) {
    var height = 50;
    var width = 94;
    //Draw Graph
    var shot_chart = d3.select('#shot_chart')
        .append('svg')
        .attr('width', width*multiplier)
        .attr('height', height*multiplier)

    //Court
    //paint
    var court = shot_chart.append('g')
    court.append('rect')
              .attr('x', 0*multiplier)
              .attr('y', (height-16)/2*multiplier)
              .attr('height', 16*multiplier)
              .attr('width', (18+10/12)*multiplier)
              .attr('fill', 'None')
              .attr('stroke', 'black')          
    court.append('rect')
              .attr('x', (width-(18+10/12))*multiplier)
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
    court.append('circle')
              .attr('cx', (width-(18+10/12))*multiplier)
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
    court.append('line')
              .attr('x1', (width-4)*multiplier)
              .attr('x2', (width-4)*multiplier)
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
    court.append('line')
              .attr('x1', width*multiplier)
              .attr('x2', (width-14)*multiplier)
              .attr('y1', (height-3)*multiplier)
              .attr('y2', (height-3)*multiplier)
              .attr('stroke', 'black')
    court.append('path')
         .attr('d', 'M' + (width-14)*multiplier + ', ' + 3*multiplier + ' ' +
                    'A' + (28)*multiplier + ', ' + (height/2)*multiplier 
                        + ' 0 0,0 ' 
                        + (width-28)*multiplier + ', ' + height/2*multiplier 
                        + ' ' +
                    'A' + (28)*multiplier + ', ' + (height/2)*multiplier 
                        + ' 0 0,0 ' 
                        + (width-14)*multiplier + ', ' + (height-3)*multiplier)
         .attr('fill', 'None')
         .attr('stroke', 'black')
    return court;
};
              
var draw_shots = function(shot_data, multiplier, shot_radius) {
    var shot_chart = d3.select('#shot_chart svg');
    d3.select('#shots').remove();
    var shots = shot_chart.append('g')
                          .attr('id', 'shots')
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
    shot.append('svg:ul')
        .attr('x', function(shot) {
                        return shot.y * multiplier;
                    })
        .attr('y', function(shot){
                        return shot.x * multiplier;
                    })
        .attr('class', 'shot_info')
        .attr('id', function(shot){
                        return shot.id;
                    })
        .text(function(shot) {
            $('#' + shot.id).append('li').text('hello')
        })
        
};











