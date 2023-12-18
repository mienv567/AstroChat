/* ================================================================= */
/* CSS Style Switcher By FIFO THEMES
====================================================================== */

window.console = window.console || (function(){
	var c = {}; c.log = c.warn = c.debug = c.info = c.error = c.time = c.dir = c.profile = c.clear = c.exception = c.trace = c.assert = function(){};
	return c;
})();


jQuery(document).ready(function($) {
	
		// Color Changer
		
		$(".blue" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/blue.css" );
			saveColorConfig('blue');
			return false;
		});
		
		$(".green" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/green.css" );
			saveColorConfig('green');
			return false;
		});
		
		$(".orange" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/orange.css" );
			saveColorConfig('orange');
			return false;
		});
		
		
		$(".purple" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/purple.css" );
			saveColorConfig('purple');
			return false;
		});

		$(".red" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/red.css" );
			saveColorConfig('red');
			return false;
		});

		$(".magenta" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/magenta.css" );
			saveColorConfig('magenta');
			return false;
		});
		
		
		$(".brown" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/brown.css" );
			saveColorConfig('brown');
			return false;
		});
		
		$(".gray" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/gray.css" );
			saveColorConfig('gray');
			return false;
		});
		
		$(".teal" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/teal.css" );
			saveColorConfig('teal');
			return false;
		});
		
		$(".golden" ).click(function(){
			$(".colors" ).attr("href", "/statics/css/colors/golden.css" );
			saveColorConfig('golden');
			return false;
		});
		

		$("#style-switcher h2 a").click(function(e){
			e.preventDefault();
			var div = $("#style-switcher");
			console.log(div.css("left"));
			if (div.css("left") === "-206px") {
				$("#style-switcher").animate({
					left: "0px"
				}); 
			} else {
				$("#style-switcher").animate({
					left: "-206px"
				});
			}
		});
		
		function saveColorConfig(color){
			$.cookie('web_color',color, {path:'/'});			
		}

		$("#layout-switcher").on('change', function() {
			$('#layout').attr('href', $(this).val() + '.css');			
		});

		$(".colors li a").click(function(e){
			e.preventDefault();
			$(this).parent().parent().find("a").removeClass("active");
			$(this).addClass("active");
		});
			

	});