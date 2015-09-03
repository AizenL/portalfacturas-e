openerp.portalfacturas = function(instance) {

	instance.web.SearchViewDrawer.include({

	    start: function() {
            this.toggle(true);
            this._super();
        },
    });
};