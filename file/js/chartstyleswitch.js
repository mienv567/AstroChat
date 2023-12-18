/**
* Styleswitch stylesheet switcher built on jQuery
* Under an Attribution, Share Alike License
* By Kelvin Luck ( http://www.kelvinluck.com/ )
**/

(function($)
{
	// cookie functions http://www.quirksmode.org/js/cookies.html
	function createCookie(name,value,days)
	{
		if (days)
		{
			var date = new Date();
			date.setTime(date.getTime()+(days*86400000));
			var expires = "; expires="+date.toGMTString();
		}
		else var expires = "";
		document.cookie = name+"="+value+expires+"; path=/";
	}
	function readCookie(name)
	{
		var nameEQ = name + "=";
		var ca = document.cookie.split(';');
		for(var i=0;i < ca.length;i++)
		{
			var c = ca[i];
			while (c.charAt(0)==' ') c = c.substring(1,c.length);
			if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
		}
		return null;
	}
	function eraseCookie(name)
	{
		createCookie(name,"",-1);
	}
	// /cookie functions

	$(document).ready(function() {		
		$('.chartstyleswitch').click(function()
		{			
			switchStylestyle(this.getAttribute("rel"));
			return false;
		});
		var c = readCookie('chart_style');
		if (c) switchStylestyle(c);
	});

	function switchStylestyle(styleName)
	{
		$('link[rel*=style][title]').each(function(i) 
		{
            title = this.getAttribute('title') ;            
            if (title.indexOf("chart-") >= 0)
            {              
                //alert(title);
                this.disabled = true;
                if (title == styleName) this.disabled = false;
            }
		});
		createCookie('chart_style', styleName, 365);
	}
})(jQuery);
