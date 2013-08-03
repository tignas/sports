{ 
        "bPaginate": false,
        "bLengthChange": false,
        "bInfo": false,
        "bAutoWidth": false,
        "aaSorting": [[ 16, "desc" ], [0, "asc"]],
        "aoColumnDefs":[
            {"bSortable": false, "aTargets":[0, 1, 2]}
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
    }
