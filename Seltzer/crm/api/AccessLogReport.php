<?php

?>
<html>
    <head>
        <!--jQuery-->
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.3/jquery.min.js"></script>

        <!--JQ Widgets-->
        <link rel="stylesheet" href="jqwidgets/styles/jqx.base.css" type="text/css" />
        <script type="text/javascript" src="jqwidgets/jqxcore.js"></script>
        <script type="text/javascript" src="jqwidgets/jqxdata.js"></script> 
        <script type="text/javascript" src="jqwidgets/jqxbuttons.js"></script>
        <script type="text/javascript" src="jqwidgets/jqxscrollbar.js"></script>
        <script type="text/javascript" src="jqwidgets/jqxmenu.js"></script>
        <script type="text/javascript" src="jqwidgets/jqxcheckbox.js"></script>
        <script type="text/javascript" src="jqwidgets/jqxlistbox.js"></script>
        <script type="text/javascript" src="jqwidgets/jqxdropdownlist.js"></script>
        <script type="text/javascript" src="jqwidgets/jqxgrid.js"></script>
        <script type="text/javascript" src="jqwidgets/jqxgrid.sort.js"></script> 
        <script type="text/javascript" src="jqwidgets/jqxgrid.pager.js"></script> 
        <script type="text/javascript" src="jqwidgets/jqxgrid.selection.js"></script> 
        <script type="text/javascript" src="jqwidgets/jqxgrid.edit.js"></script>    
        <script type="text/javascript" src="jqwidgets/jqxgrid.filter.js"></script> 

        <style>
        html, body{width: 100%; height: 100%; overflow: hidden; padding:0px; }
        </style>
        
        <script type="text/javascript">
    $(document).ready(function () {
    var url = 'query.php?action=getAccessLog';

        
        
    // prepare the data
    var source =
        {
            datatype: "json",
            datafields: [
                { name: 'member', type: 'string' },
				{ name: 'access', type: 'integer' },
				{ name: 'reason', type: 'string' },
                { name: 'swipetime', type: 'date' }
            ],
            id: 'cid',
            url: url
        };

    var dataAdapter = new $.jqx.dataAdapter(source, {
        downloadComplete: function (data, status, xhr) { },
        loadComplete: function (data) {
            //$('#memberCount').text(' (' + dataAdapter.records.length + ' Active)');
        },
        loadError: function (xhr, status, error) { }
    });

    // initialize jqxGrid
    $("#jqxgrid").jqxGrid(
        {
            width: '98%',
                height: '78%',
            source: dataAdapter,
            pagermode: "simple",
            pagesize: 12,
            pageable: false,
            selectionmode: 'singlecell',
            filterable: true,
            sortable: true,
            editable: false,
            columns: [
			  { text: 'Member', displayfield: 'member', width:150},
			  { text: 'Access Granted?', displayfield: 'access', width:100, cellsalign:'center',
                  cellsrenderer: function (row, columnfield, value, defaulthtml, columnproperties) {
                    if(value == 1)
					{
					 return '<span style="color:green; font-weight:bold">Yes!</span>';
					}
					else
					{
						return '<span style="color:red; font-weight:bold">No!</span>';	
					}
					
					
				}   
              
              },
			  { text: 'Reason', displayfield: 'reason', width:250},
			  { text: 'Date/Time', displayfield: 'swipetime',  filtertype: 'date', width: 250, cellsformat: 'MM/dd/yyyy h:mm' }
            ],
            groupable: false
        });
        
        //console.log(dataAdapter);
        
        
        
    });
    </script>
        </head>
    <body>
    <h2>
        Recent Access Log
    </h2>
    <div id='jqxWidget' style="font-size: 13px; font-family: Verdana; float: left; width:100%;">
        <div id="jqxgrid">
        </div>
    </div>
    </body>
</html>