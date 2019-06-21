class MultipleSelectFilterWidgetManager {

    constructor(neighbors, items, initial) {
        this.inputs = [];
        this.graph_neighbors = neighbors;
        this.filter_items = items;
        this.result = {};
        this.dropdown_count = 0;
        this.make_selection(initial);

        for(var nodeId in this.filter_items) {
            var node = this.filter_items[nodeId];
            this.result[node.class] = {}
        }
    }
    
    make_selection( initial_data ){
        if(!initial_data || jQuery.isEmptyObject(initial_data))
            return;
        for(var item_class in initial_data) {
            var selected_items = initial_data[item_class];
            for( var node_id in selected_items ){
                var node = this.filter_items[node_id];
                var selection_data = selected_items[node_id]
                if( selection_data.selected ) {
                    this.select(node);
                    this.markAndSweep(node);
                    this.updateResult(node);
                }
                if(node['multiple']){
                    this.make_multiple_selection(node, selection_data);
                }
            }
        }
    }

    make_multiple_selection(node, selection_data){
        prepop_data = selection_data.values;
        for(var k in prepop_data){
            var div = add_item_prepopulate(node, prepop_data[k]);
            updateObjectResult(node, div.id, prepop_data[k]);
        }
    }

    markAndSweep(root){
        for(var i in this.filter_items) {
            var node = this.filter_items[i];
            node['marked'] = true; //mark all nodes
        }

        var toCheck = [root];
        while(toCheck.length > 0){
            var node = toCheck.pop();
            if(!node['marked']) {
                continue; //already visited, just continue
            }
            node['marked'] = false; //mark as visited
            if(node['follow'] || node == root){ //add neighbors if we want to follow this node
                var neighbors = this.graph_neighbors[node.id];
                for(var i in neighbors) {
                    var neighId = neighbors[i];
                    var neighbor = this.filter_items[neighId];
                    toCheck.push(neighbor);
                }
            }
        }

        //now remove all nodes still marked
        for(var i in this.filter_items){
            node = this.filter_items[i];
            if(node['marked']){
                this.disable_node(node);
            }
        }
    }

    process(node) {
        if(node['selected']) {
            this.markAndSweep(node);
        }
        else {  //TODO: make this not dumb
            var selected = []
            //remember the currently selected, then reset everything and reselect one at a time
            for(var nodeId in this.filter_items) {
                node = this.filter_items[nodeId];
                if(node['selected']) {
                    selected.push(node);
                }
                this.clear(node);
            }
            for(var i=0; i<selected.length; i++) {
                node = selected[i];
                this.select(node);
                this.markAndSweep(selected[i]);
            }
        }
    }

    select(node) {
        var elem = document.getElementById(node['id']);
        node['selected'] = true;
        elem.classList.remove('disabled_node', 'cleared_node');
        elem.classList.add('selected_node');
    }

    clear(node) {
        var elem = document.getElementById(node['id']);
        node['selected'] = false;
        node['selectable'] = true;
        elem.classList.add('cleared_node')
        elem.classList.remove('disabled_node', 'selected_node');
    }

    disable_node(node) {
        var elem = document.getElementById(node['id']);
        node['selected'] = false;
        node['selectable'] = false;
        elem.classList.remove('cleared_node', 'selected_node');
        elem.classList.add('disabled_node');
    }

    processClick(id){
        var node = this.filter_items[id];
        if(!node['selectable'])
            return;

        if(node['multiple']){
            return this.processClickMultiple(node);
        } else {
            return this.processClickSingle(node);
        }
    }

    processClickSingle(node){
        node['selected'] = !node['selected']; //toggle on click
        if(node['selected']) {
            this.select(node);
        } else {
            this.clear(node);
        }
        this.process(node);
        this.updateResult(node);
    }

    processClickMultiple(node){
        this.select(node);
        var div = this.add_item_prepopulate(node, false);
        this.process(node);
        this.updateObjectResult(node, div.id, "");
    }

    restrictchars(input){
        if( input.validity.patternMismatch ){
            input.setCustomValidity("Only alphanumeric characters (a-z, A-Z, 0-9), underscore(_), and hyphen (-) are allowed");
            input.reportValidity();
        }
        input.value = input.value.replace(/([^A-Za-z0-9-_.])+/g, "");
        this.checkunique(input);
    }

    checkunique(tocheck){ //TODO: use set
        var val = tocheck.value;
        for( var i in this.inputs ){
            if( this.inputs[i].value == val && this.inputs[i] != tocheck){
                tocheck.setCustomValidity("All hostnames must be unique");
                tocheck.reportValidity();
                return;
            }
        }
        tocheck.setCustomValidity("");
    }

    make_remove_button(div, node){
        var button = document.createElement("BUTTON");
        button.type = "button";
        button.appendChild(document.createTextNode("Remove"));
        button.classList.add("btn", "btn-danger");
        button.onclick = function(){ this.remove_dropdown(div.id, node.id); }
        return button;
    }

    make_input(div, node, prepopulate){
        var input = document.createElement("INPUT");
        input.type = node.form.type;
        input.name = node.id + node.form.name
        input.pattern = "(?=^.{1,253}$)(^([A-Za-z0-9-_]{1,62}\.)*[A-Za-z0-9-_]{1,63})";
        input.title = "Only alphanumeric characters (a-z, A-Z, 0-9), underscore(_), and hyphen (-) are allowed"
        input.placeholder = node.form.placeholder;
        this.inputs.push(input);
        var me = this;
        input.onchange = function() { me.updateObjectResult(node, div.id, input.value); me.restrictchars(this); };
        input.oninput = function() { me.restrictchars(this); };
        if(prepopulate)
            input.value = prepopulate;
        return input;
    }

    add_item_prepopulate(node, prepopulate){
        var div = document.createElement("DIV");
        div.id = "dropdown_" + this.dropdown_count;
        div.classList.add("dropdown_item");
        this.dropdown_count++;
        var label = document.createElement("H5")
        label.appendChild(document.createTextNode(node['name']))
        div.appendChild(label);
        div.appendChild(this.make_input(div, node, prepopulate));
        div.appendChild(this.make_remove_button(div, node));
        document.getElementById("dropdown_wrapper").appendChild(div);
        return div;
    }

    remove_dropdown(div_id, node_id){
        var div = document.getElementById(div_id);
        var node = this.filter_items[node_id]
        var parent = div.parentNode;
        div.parentNode.removeChild(div);
        delete this.result[node.class][node.id]['values'][div.id];

        //checks if we have removed last item in class
        if(jQuery.isEmptyObject(this.result[node.class][node.id]['values'])){
            delete this.result[node.class][node.id];
            this.clear(node);
        }
    }

    updateResult(node){
        if(!node['multiple']){
            this.result[node.class][node.id] = {selected: node.selected, id: node.model_id}
            if(!node.selected)
                delete this.result[node.class][node.id];
        }
    }

    updateObjectResult(node, childKey, childValue){
        if(!this.result[node.class][node.id])
            this.result[node.class][node.id] = {selected: true, id: node.model_id, values: {}}

        this.result[node.class][node.id]['values'][childKey] = childValue;
    }
}
