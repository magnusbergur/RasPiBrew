
//declare globals
var dataStore, options_temp, options_heat, plot, showLines, controllerValues;
var capture_on = 1;
var captureWindowSize, areSensorsSet = 0;


$(window).unload(function() {
	cacheData()
    console.log('Cached data');
});

function showTooltip(x, y, contents)
{
	jQuery('<div id="tooltip">' + contents + '</div>').css({
		position : 'absolute',
		display : 'none',
		top : y + 5,
		left : x + 5,
		border : '1px solid #fdd',
		padding : '2px',
		'background-color' : '#fee',
		opacity : 0.80
	}).appendTo("body").fadeIn(200);
}

function storeData(data) {	
	var timestamp = Date(data.time);

	for(var key in data){
		if(key == "time") continue;
	
		dataStore[key].push([timestamp, parseFloat(data[key])])
	}	
}

function plotData()
{
	var inner_series       = { label: "Inside",      data: dataStore["innerTemp"].slice(dataStore["innerTemp"]-captureWindowSize) };
	var inner_set_series   = { label: "I-set", 		 data: dataStore["innerSet"].slice(dataStore["innerSet"]-captureWindowSize) };
	var outer_series       = { label: "Outside",     data: dataStore["outerTemp"].slice(dataStore["outerTemp"]-captureWindowSize) };
	var outer_set_series   = { label: "O-set", 		 data: dataStore["outerSet"].slice(dataStore["outerSet"]-captureWindowSize) };
	var environment_series = { label: "Environment", data: dataStore["envirTemp"].slice(dataStore["envirTemp"]-captureWindowSize) };
	var basedata = [inner_series, inner_set_series, outer_series, outer_set_series, environment_series]

	var data = []
	for (var i = 0; i < 5; i++) {
		if (showLines[i] == 1) {
			data.push(basedata[i])
		}
	}

	plot = jQuery.plot($("#tempplot"), data, options_temp);
	plot = jQuery.plot($("#heatplot"), [dataStore["duty"]], options_heat);
}

function requestHistoryMsg()
{
	var idx = dataStore["innerTemp"].length;
	console.log("request hist at",idx);

	jQuery.ajax({
		type : "GET",
		url : "/gethistory/",
		data : {'indx':idx},
		dataType : "json",
		async : true,
		cache : false,
		timeout : 50000,

		success : function(data)
		{
			console.log("history data ",data)

			if(data.hasOwnProperty("innerTemp")){
				for(var key in data){
					if(key == "time") continue;

					var values = data[key]
					for(var i=0; i<data[key].length; i++){
						dataStore[key].push([data["time"][i], parseFloat(data[key][i])])
					}
				}

				
			}

			//setTimeout('waitForMsg()', 1); //in millisec
		}
	});
}

//long polling - wait for message
function waitForMsg()
{
	jQuery.ajax({
		type : "GET",
		url : "/getstatus/",
		dataType : "json",
		async : true,
		cache : false,
		timeout : 50000,

		success : function(data)
		{
			//console.log(data)

			jQuery('#tempResponseInner').html(data.innerTemp);
			jQuery('#tempResponseOuter').html(data.outerTemp);
			jQuery('#tempResponseEnvir').html(data.envirTemp);
			jQuery('#dutycycleResponse').html(data.duty.toFixed(2));

			storeData(data);

			if (capture_on == 1)
			{
				plotData();
				setTimeout('waitForMsg()', 1); //in millisec
			}
		}
	});
};

function initializeData() {
	console.log( "Initialize data" );
	showLines = [1,0,1,0,1];
	captureWindowSize = 1000000
	controllerValues = {mode:"off",setpoint:0,dutycycle:0,cycletime:0,deadband:0,kC:0,iC:0,dC:0,kH:0,iH:0,dH:0};
	resetPlotData();

	document.getElementById("windowSizeText").value = captureWindowSize;
}

function resetPlotData() {
	console.log( "reset plot data" );
	dataStore = {"innerTemp":[], "outerTemp":[], "envirTemp":[], "innerSet":[], "outerSet":[], "duty":[]};
	cacheData();
}

function retrieveData() {
	console.log( "Retrieve data" );
	dataStore = JSON.parse(localStorage.getItem("dataStoreStoreFerm"));
	showLines = JSON.parse(localStorage.getItem("showLinesFerm"));
	controllerValues = JSON.parse(localStorage.getItem("controllerValuesFerm"));
	captureWindowSize = JSON.parse(localStorage.getItem("cacheWindowSizeStoreFerm"));	
	console.log('History size: '+dataStore["innerTemp"].length)

	document.getElementById("windowSizeText").value = captureWindowSize;
}

function cacheData() {
	console.log( "Cache data" );
	localStorage.setItem("dataStoreStoreFerm", JSON.stringify(dataStore))
	localStorage.setItem("showLinesFerm", JSON.stringify(showLines));
	localStorage.setItem("controllerValuesFerm", JSON.stringify(controllerValues));
	localStorage.setItem("cacheWindowSizeStoreFerm", JSON.stringify(captureWindowSize));
}

function selectLinesToShow()  {
	for (l = 1; l < 6; l++) {
		if(showLines[l-1] == 0) {
			$('#Chbx'+l).prop('checked', false);
		}	
	}
} 

jQuery(document).ready(function() {
	
	jQuery('#stop').click(function() {
		capture_on = 0;
	});
	jQuery('#restart').click(function() {
		capture_on = 1;
		resetPlotData()
		console.log( "restart plot" );
		waitForMsg();
	});

	var previousPoint = null;
	jQuery("#tempplot").bind("plothover", function(event, pos, item) {
		if (item) {
			if (previousPoint != item.dataIndex) {
				previousPoint = item.dataIndex;

				jQuery("#tooltip").remove();
				var x = item.datapoint[0].toFixed(2), y = item.datapoint[1].toFixed(2);

				showTooltip(item.pageX, item.pageY, "(" + x + ", " + y + ")");
			}
		} else {
			jQuery("#tooltip").remove();
			previousPoint = null;
		}

	});

	$("#ToggleLines").find("input[type='checkbox']").click(function () {
	    var position = $(this).attr("id").replace("Chbx", "");
	    position = parseInt(position) - 1;
	    
	    if ($(this).is(":checked")) {
	        showLines[position] = 1;
	    } else {
			showLines[position] = 0;
	    }
    });

	jQuery('#controlPanelForm').submit(function() {

		formdata = jQuery(this).serialize();

		jQuery.ajax({
		type : "POST",
		url : "/postparams/",
		data : formdata,
		success : function(data){},
		});

		return false;
	});

	if(document.cookie.indexOf('myFermCookie')==-1){
	    document.cookie = 'myFermCookie=1';

    	initializeData()
	} else {
		initializeData()
	    //retrieveData()
	}
	selectLinesToShow();

	jQuery('#windowSizeText').change(function() {
		console.log( "windowSizeText changed" );
		captureWindowSize = jQuery('#windowSizeText').val()
	});
	
	options_temp = {
		series : {
			lines : {
				show : true
			},
			//points: {show: true},
			shadowSize : 0
		},
		yaxis : {
			min : null,
			max : null
		},
		xaxis : {
			show : true,
			mode : "time"
		},
		grid : {
			hoverable : true
			//  clickable: true
		},
		selection : {
			mode : "x"
		},
		legend : {
			position: "nw"
		}

	};

	options_heat = {
		series : {
			lines : {
				show : true
			},
			//points: {show: true},
			shadowSize : 0
		},
		yaxis : {
			min : -100,
			max : 100
		},
		xaxis : {
			show : true,
			mode : "time"
		},
		selection : {
			mode : "x"
		}
	};


	requestHistoryMsg();
});
