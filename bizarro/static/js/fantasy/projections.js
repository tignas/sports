$(document).ready(function () {

$('#keepers_submit').on('click', function () {
    var keeper_inputs = $('input[name="keepers"][value!=""]');
    var url = '?'
    $.each(keeper_inputs, function(k, v) {
        if ($(v).data('playerId')) {
            url += 'player_keeper_'+k+'_id='+$(v).data('playerId')+'&';
            url += 'player_keeper_'+k+'_val='+$(v).val()+'&';
        } else {
            url += 'team_keeper_'+k+'_id=' + $(v).data('teamId')+'&';
            url += 'team_keeper_'+k+'_val=' + $(v).val()+'&';
        }
    });
    window.location.href = url;
});

var initialize_table = function () { 
    var player_table = $('#player_table').dataTable({ 
        "bPaginate": false,
        "bLengthChange": false,
        "bInfo": false,
        "bAutoWidth": false,
        "aaSorting": [[ 16, "desc" ], [0, "asc"]],
        "aoColumnDefs":[
            {"bSortable": false, "aTargets":[0, 1, 2, 3]}
            ],
        "sDom": 't',
        "fnDrawCallback": function ( oSettings ) {
            var that = this;
            if ( oSettings.bSorted || oSettings.bFiltered ) {            
                this.$('td:first-child', {"filter":"applied"})
                    .each( function (i){
                        that.fnUpdate( i+1, this.parentNode, 0, false, false );
                    });
            };
        },
    });
    return player_table;
};

player_table = initialize_table();


$('#player_search').live('keyup', function () {
    player_table.fnFilter($(this).val(), 1);
});

$('#team').live('change', function () {
    player_table.fnFilter( $(this).val(), 3);
});

$('#keeper_switch').on('change', function () {
    var tog = $('#keeper_switch:checked');
    if (tog.length) {
        $('.keeper').show();
        tog.attr('name', 'keeper');
    } else {
        $('.keeper').hide();
    }
});
$('.keeper').on('change', function () {
    var input = $(this).find('input');
    var player_id = input.data('playerId');
    input.attr('name', 'keeper_'+player_id);
    if (!(input.val())) {
        input.removeAttr('name');
    }
});

$('#baseline_switch').on('change', function () {
    baseline_toggle();
});
var baseline_toggle = function () {
    var checked = $('#baseline_switch').is(':checked');
    if (checked) {
        $('.baseline').prop('disabled', false);
    } else {
        $('.baseline').prop('disabled', true);            
    }
};

baseline_toggle();

});
