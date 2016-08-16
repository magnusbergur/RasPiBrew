
//declare globals
var tempDataArray, heatDataArray, setpointDataArray, options_temp, options_heat, plot, showLines, controllerValues;
var capture_on = 1;
var temp, setpoint, captureWindowSize, areSensorsSet = 0;


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

function pushData(timeseries, timestamp, value) {
	timeseries.push([timestamp, parseFloat(value)]);
	while (timeseries.length > captureWindowSize) {
		timeseries.shift();
	}
}

"time": timestamp, "innerTemp": innerTemp, "outerTemp": outerTemp, "envirTemp":envirTemp, "duty":duty

function storeData(data) {	
	var timestamp = Date(data.time);

	pushData(tempDataArray["inner"], timestamp, data.innerTemp)
	pushData(tempDataArray["outer"], timestamp, data.outerTemp)
	pushData(tempDataArray["envir"], timestamp, data.envirTemp)
	pushData(setpointDataArray["inner"], timestamp, data.innerSetpoint)
	pushData(heatDataArray["duty"], timestamp, data.duty)
}

function plotData()
{
	var inner_series       = { label: "Inside",      data: tempDataArray["inner"] };
	var inner_set_series   = { label: "I-set", 		 data: setpointDataArray["inner"] };
	var outer_series       = { label: "Outside",     data: tempDataArray["outer"] };
	var outer_set_series   = //{ label: "O-set", 		 data: setpointDataArray"outer"] };
	var environment_series = { label: "Environment", data: tempDataArray["envir"] };
	var basedata = [inner_series, inner_set_series, outer_series, outer_set_series, environment_series]

	data = []
	for (i = 0; i < 5; i++) {
		if (showLines[i] == 1) {
			data.push(basedata[i])
		}
	}

	plot = jQuery.plot($("#tempplot"), data, options_temp);
	plot = jQuery.plot($("#heatplot"), [heatDataArray["inner"]], options_heat);
}

/*function controllerSetup()
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
			var sensor = data.sensor;

			jQuery('#tempResponse'+sensor).html(data.temp);
			jQuery('#setpointResponse'+sensor).html(data.set_point);
			jQuery('#dutycycleResponse'+sensor).html(data.duty_cycle.toFixed(2));

			storeData(sensor-1, data);

			if (capture_on == 1 && sensor == 1)
			{
				plotData();
				if(areSensorsSet == 0)
				{
					controllerValues.mode = data.mode;
					controllerValues.setpoint = data.set_point;
					controllerValues.dutycycle = data.duty_cycle;
					controllerValues.cycletime = data.cycle_time;
					controllerValues.deadband = data.deadband;
					controllerValues.kH = data.kH;
					controllerValues.iH = data.iH;
					controllerValues.dH = data.dH;
					controllerValues.kC = data.kC;
					controllerValues.iC = data.iC;
					controllerValues.dC = data.dC;

					setPIDParams();
					areSensorsSet = 1;
				}
					
				setTimeout('waitForMsg()', 1); //in millisec
			}
		}
	});
};*/

function requestHistoryMsg()
{
	var idx = [tempDataArray[0].length, tempDataArray[1].length, tempDataArray[2].length];
	console.log("request hist at",idx)
	jQuery.ajax({
		type : "GET",
		url : "/gethistory/",
		data : {indx: idx},
		dataType : "json",
		async : true,
		cache : false,
		timeout : 50000,

		success : function(data)
		{
			var S = Object.keys(data).length
			console.log("first data ",S)
			for(s = 0; s < S; s++){
				tempDataArray[s].concat(data[s])
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
	tempDataArray = {"inner":[], "outer":[], "envir":[]];
	heatDataArray = {"inner":[]};
	setpointDataArray = {"inner":[], "outer":[]};
	cacheData();
}

function retrieveData() {
	console.log( "Retrieve data" );
	tempDataArray = JSON.parse(localStorage.getItem("tempDataArrayStoreFerm"));
	heatDataArray = JSON.parse(localStorage.getItem("heatDataArrayStoreFerm"));
	setpointDataArray = JSON.parse(localStorage.getItem("setpointDataArrayStoreFerm"));
	showLines = JSON.parse(localStorage.getItem("showLinesFerm"));
	controllerValues = JSON.parse(localStorage.getItem("controllerValuesFerm"));
	captureWindowSize = JSON.parse(localStorage.getItem("cacheWindowSizeStoreFerm"));	
	console.log('History size: '+tempDataArray["inner"].length)

	document.getElementById("windowSizeText").value = captureWindowSize;
}

function cacheData() {
	console.log( "Cache data" );
	localStorage.setItem("tempDataArrayStoreFerm", JSON.stringify(tempDataArray))
	localStorage.setItem("heatDataArrayStoreFerm", JSON.stringify(heatDataArray));
	localStorage.setItem("setpointDataArrayStoreFerm", JSON.stringify(setpointDataArray));
	localStorage.setItem("showLinesFerm", JSON.stringify(showLines));
	localStorage.setItem("controllerValuesFerm", JSON.stringify(controllerValues));
	localStorage.setItem("cacheWindowSizeStoreFerm", JSON.stringify(captureWindowSize));
}

function setInitialPIDParams() {
	//console.log("setPIDParams")
	//console.log(controllerValues)
	$('.modeBtn').removeClass("active");
	$('#modeBtn_'+controllerValues.mode).addClass('active');
	$('#mode_'+controllerValues.mode).prop('checked', true);

	$('#setpoint').val(controllerValues.setpoint);
	$('#deadband').val(controllerValues.deadband);
	$('#dutycycle').val(controllerValues.dutycycle);
	$('#cycletime').val(controllerValues.cycletime);
	$('#kcH_param').val(controllerValues.kH);
	$('#tiH_param').val(controllerValues.iH);
	$('#tdH_param').val(controllerValues.dH);
	$('#kcC_param').val(controllerValues.kC);
	$('#tiC_param').val(controllerValues.iC);
	$('#tdC_param').val(controllerValues.dC);
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
